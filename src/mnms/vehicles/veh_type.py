from __future__ import annotations

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from mnms.graph.graph_path import GraphPath
from mnms.graph.link_descriptor import LinkDescriptor
from mnms.log import create_logger
from mnms.time import Dt, Time
from mnms.tools.observer import TimeDependentSubject

log = create_logger(__name__)
_norm = np.linalg.norm


class ActivityType(Enum):
    """Enumerate activity types."""

    STOP = 0
    REPOSITIONING = 1
    PICKUP = 2
    SERVING = 3


def _check_link_lengths(path: GraphPath, link_lengths: list[float]):
    if len(link_lengths) != len(path.links):
        raise ValueError(f'Inconsistent link lengths {link_lengths} for path {path}')


@dataclass(slots=True)
class VehicleActivity(ABC):
    """Class representing a vehicle activity.

        Attributes:
            activity_type (ActivityType): the type of the activity
            is_moving (bool): indicates if the vehicle moves or not during the activity
            path (GraphPath): the path linked to the activity
            link_lengths (list[float]): the length to travel on each link of the path
                (len(link_lengths) == len(path.links))
            user: the user linked to the activity
            is_done: indicates if the activity is terminated
    """
    activity_type: ActivityType
    is_moving: bool

    path: GraphPath
    link_lengths: list[float]
    user: "User" = None
    is_done: bool = False

    # Execution state:
    # _next_link_index: index of the next link of the path to be entered by the vehicle
    #     (0 <= _next_link_index <= len(path.links)):
    #     - 0: the vehicle has not entered any link of the path yet,
    #     - i > 0: the vehicle is on the link at index i-1 (i.e. it is traveling it, or it has just reached its end).
    _next_link_index: int = field(default=0, init=False) # Execution state, see class documentation

    def __post_init__(self):
        _check_link_lengths(self.path, self.link_lengths)

    @property
    def node(self) -> str: # TODO OrientedGraphPath remove or rename?
        return self.path.destination

    def next_link(self) -> tuple[LinkDescriptor, float]:
        """Return the next link of the path to travel, and the length to travel on it.

        Raises:
            -StopIteration: if the end of the path is reached
        """
        index = self._next_link_index
        if index >= len(self.path.links):
            raise StopIteration
        self._next_link_index += 1
        return LinkDescriptor.from_path(self.path, index), self.link_lengths[index]

    def modify_path(self, new_path: GraphPath, new_link_lengths: list[float]):
        """Method to update this activity path.

        Args:
            -new_path: the new path
            -new_link_lengths: the length to travel on each link of the new path
        """
        _check_link_lengths(new_path, new_link_lengths)
        self.path = new_path
        self.link_lengths = new_link_lengths
        self._next_link_index = 0

    def modify_path_and_next(self, new_path: GraphPath, new_link_lengths: list[float]):
        """Method to update this activity path and set the iterator on path to the next node.

        Args:
            -new_path: the new path
            -new_link_lengths: the length to travel on each link of the new path
        """
        self.modify_path(new_path, new_link_lengths)
        self.next_link()

    def sub_path(self, pos: int, link_count: int | None = None) -> tuple[GraphPath, list[float]]:
        """Return a part of the path of this activity, and the corresponding link lengths.

        Args:
            -pos, link_count: same as GraphPath.sub_path

        Returns:
            -path: the part of path (same as GraphPath.sub_path)
            -link_lengths: the length to travel on each link of the part of path

        Raises:
            -same as GraphPath.sub_path
        """
        path = self.path.sub_path(pos, link_count)
        return path, self.link_lengths[pos:pos+len(path.links)]

    @abstractmethod
    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done (abstract method)

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        return

    @abstractmethod
    def start(self, veh: "Vehicle"):
        """Update when the activity is started (abstract method)

            Parameters:
                veh (Vehicle): The vehicle performing the activity
        """

        return

    def copy(self):
        return self.__class__(path=self.path,
                              link_lengths=self.link_lengths.copy(),
                              user=self.user,
                              is_done=self.is_done)


@dataclass(slots=True)
class VehicleActivityStop(VehicleActivity):
    """Class representing a no activity."""

    activity_type: ActivityType = field(default=ActivityType.STOP, init=False)
    is_moving: bool = field(default=False, init=False)

    @classmethod
    def at_node(cls, node: str, is_done: bool = False) -> VehicleActivityStop:
        """Build a stop activity at the given node (i.e. with a path made of this single node and no link)."""
        return cls(path=GraphPath([node], []), link_lengths=[], is_done=is_done)

    def start(self, veh: "Vehicle"):
        """Update when the activity is started

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        return

    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        if self.user is not None:
            self.user.vehicle = veh


@dataclass(slots=True)
class VehicleActivityRepositioning(VehicleActivity):
    """Class representing a repositionning activity."""

    activity_type: ActivityType = field(default=ActivityType.REPOSITIONING, init=False)
    is_moving: bool = field(default=True, init=False)

    def start(self, veh: "Vehicle"):
        """Update when the activity is started

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        return

    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        return


@dataclass(slots=True)
class VehicleActivityPickup(VehicleActivity):
    """Class representing a pick-up activity."""
    activity_type: ActivityType = field(default=ActivityType.PICKUP, init=False)
    is_moving: bool = field(default=True, init=False)

    def start(self, veh: "Vehicle"):
        """Update when the activity is started

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        self.user.set_state_waiting_vehicle(veh)

    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """

        self.user.vehicle = veh
        veh.passengers[self.user.id] = self.user
        self.user.set_state_inside_vehicle()


@dataclass(slots=True)
class VehicleActivityServing(VehicleActivity):
    """Class representing a serving activity."""
    activity_type: ActivityType = field(default=ActivityType.SERVING, init=False)
    is_moving: bool = field(default=True, init=False)

    def start(self, veh: "Vehicle"):
        """Update when the activity is started

            Parameters:
                veh (Vehicle): The vehicle performing the activities
        """
        self.user.vehicle = veh
        veh.passengers[self.user.id] = self.user
        self.user.set_state_inside_vehicle()

    def done(self, veh: "Vehicle", tcurrent: Time):
        """Update when the activity is done

             Parameters:
                 veh (Vehicle): The vehicle performing the activities
         """
        self.user.vehicle = None
        veh.passengers.pop(self.user.id)

        self.user.remaining_link_length = 0
        upath = self.user.path.graph_path
        last_achieved = False
        if veh._current_link is not None:
            if veh._current_link.downstream == veh._current_node and self.user.achieved_path and veh._current_node == \
                    self.user.achieved_path[-1]:
                last_achieved = True
            unode = veh._current_link.downstream
        else:
            unode = veh._current_node
        unode_ind = self.user.get_node_index_in_path(unode, last_achieved=last_achieved)
        ucurrent_link = LinkDescriptor.from_path(upath, unode_ind) if unode_ind < len(upath.links) else None
        self.user.set_position(ucurrent_link, unode, 0, veh.position, tcurrent)
        self.user.update_achieved_path_ms(veh.mobility_service)
        self.user.vehicle = None
        # self.user.notify(tcurrent)
        self.user.set_state_stop()
        # If this is user's personal vehicle, register location of parking and vehicle's mobility service
        # on user's side and last dropped off user on vehicle's side to prevent deletion of personal vehicle
        # before user's arrival at destination
        if veh._is_personal:
            self.user.park_personal_vehicle(veh.mobility_service, unode)
            veh.last_dropped_off_user = self.user


class Vehicle(TimeDependentSubject):
    _counter = 0

    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool,
                 activities: list[VehicleActivity] | None = None,
                 global_id: str = '-1'):
        """
        Class representing a vehicle in the simulation

        Args:
            node: The node where the Vehicle is created
            capacity: the capacity of the Vehicle
            mobility_service: The associated mobility service
            activities: The initial activities of the Vehicle
            is_personal: Boolean specifying if the vehicle is personal or not
        """
        super().__init__()

        if int(global_id) < 0:
            self._global_id = str(Vehicle._counter)
            Vehicle._counter += 1
        else:
            self._global_id = str(global_id)

        self._capacity = capacity
        self.mobility_service = mobility_service
        self._is_personal = is_personal

        self.passengers = {}  # id_user, user

        self._current_link = None
        self._current_node = node
        self._remaining_link_length = None
        self._position = None  # current vehicle coordinates
        self._distance = 0  # travelled distance ( reset to zero if other trip ?)
        self._distance_at_last_res_change = 0  # distance this vehicle has traveled since it enters current reservoir
        self.speed = None  # current speed
        self._dt_move = None
        self._achieved_path = []
        self._achieved_path_since_last_notify = []

        self.activities: deque[VehicleActivity] = deque([])
        self.activity = None  # current activity

        if activities is not None:
            self.add_activities(activities)
            self.next_activity(None)
        else:
            self.activity: VehicleActivity = self.default_activity()

    def __getstate__(self):

        state = self.__dict__.copy()
        state['_counter'] = Vehicle._counter

        return state

    def __setstate__(self, state):
        """
        This method is used during unpickling to restore the object’s state.
        """
        self.__dict__.update(state)  # Restore instance attributes
        Vehicle._counter = state['_counter']  # Restore class attribute

    def __repr__(self):
        return f"{self.__class__.__name__}('{self._global_id}', '{self.activity_type.name if self.activity_type is not None else None}')"

    @property
    def distance(self):
        return self._distance

    @property
    def distance_at_last_res_change(self):
        return self._distance_at_last_res_change

    @distance_at_last_res_change.setter
    def distance_at_last_res_change(self, d):
        self._distance_at_last_res_change = d

    @property
    def is_full(self):
        return len(self.passengers) >= self._capacity

    @property
    def capacity(self):
        return self._capacity

    @property
    def is_empty(self):
        return not bool(self.passengers)

    @property
    def id(self):
        return self._global_id

    @property
    def type(self):
        return self.__class__.__name__

    @property
    def current_link(self) -> LinkDescriptor | None:
        return self._current_link

    @property
    def current_node(self):
        return self._current_node

    @property
    def remaining_link_length(self):
        return self._remaining_link_length

    @property
    def position(self):
        return self._position

    @property
    def activity_type(self) -> ActivityType:
        return self.activity.activity_type if self.activity is not None else None

    @property
    def is_moving(self) -> bool:
        return self.activity.is_moving if self.activity is not None else False

    @property
    def dt_move(self) -> Dt:
        return self._dt_move

    @dt_move.setter
    def dt_move(self, dt):
        self._dt_move = dt

    @property
    def achieved_path(self):
        return self._achieved_path

    def update_achieved_path(self):
        if len(self.achieved_path) == 0 or self.current_node != self.achieved_path[-1]:
            self._achieved_path.append(self.current_node)
            self._achieved_path_since_last_notify.append(self.current_node)

    def flush_achieved_path_since_last_notify(self):
        self._achieved_path_since_last_notify = []

    def add_activities(self, activities: list[VehicleActivity]):
        for a in activities:
            self.activities.append(a)

    def next_activity(self, tcurrent: Time):
        if self.activity is not None:
            self.activity.done(self, tcurrent)

        try:
            activity = self.activities.popleft()
        except IndexError:
            activity = self.default_activity()

        self.activity = activity
        self.activity.start(self)
        if activity.activity_type is not ActivityType.STOP:
            if activity.path.links:
                self._current_link, self._remaining_link_length = activity.next_link()
                assert self._current_node == self._current_link.upstream, \
                    f"Veh {self.id} current node {self._current_node} is not equal to the next upstream link {self._current_link.upstream}"
            else:
                activity.is_done = True

    def override_current_activity(self):
        next_activity = self.activities.popleft()
        last_activity = self.activity
        self.activity = next_activity
        self.activity.start(self)

        if last_activity.activity_type is ActivityType.STOP:
            if next_activity.path.links:
                self._current_link, self._remaining_link_length = next_activity.next_link()
                assert self._current_node == self._current_link.upstream
            else:
                next_activity.is_done = True

    def iter_activities(self):
        yield self.activity
        yield from self.activities

    def update_distance(self, dist: float):
        self._distance += dist
        for user in self.passengers.values():
            user.update_distance(dist)

    def set_position(self, position: np.ndarray):
        self._position = position

    def drop_user(self, tcurrent: Time, user: 'User', drop_pos: np.ndarray):
        log.info(f"{user} is dropped at {self._current_link.upstream}")
        user.remaining_link_length = 0
        unode = self._current_link.upstream
        next_link = LinkDescriptor.from_path(user.path.graph_path, user.get_node_index_in_path(unode))
        user.set_position(next_link, unode, 0, drop_pos, tcurrent)
        user.vehicle = None
        user.notify(tcurrent)

        del self.passengers[user.id]

    def drop_all_passengers(self, tcurrent: Time):
        for _, user in self.passengers.values():
            log.info(f"{user} is dropped at {self._current_link.downstream}")
            unode = self._current_link.downstream
            user.current_node = unode
            user.remaining_link_length = 0
            user.position = self._position
            user.notify(tcurrent)
            user.vehicle = None

        self.passengers = {}

    def start_user_trip(self, userid, take_node):
        log.info(f'Passenger {userid} has been taken by {self} at {take_node}')
        take_time, user = self._next_passenger.pop(userid)
        user.vehicle = self.id
        self.passengers[userid] = (take_time, user)

    def default_activity(self):
        return VehicleActivityStop.at_node(self._current_node, is_done=False)

    def notify_passengers(self, tcurrent: Time):
        for user in self.passengers.values():
            user.notify(tcurrent)

    @classmethod
    def reset_counter(cls):
        cls._counter = 0


class Car(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool,
                 activities: VehicleActivity | None = None,
                 global_id: int = -1):
        super().__init__(node, capacity, mobility_service, is_personal, activities, global_id)
        self._last_dropped_off_user = None

    @property
    def last_dropped_off_user(self):
        return self._last_dropped_off_user

    @last_dropped_off_user.setter
    def last_dropped_off_user(self, user):
        self._last_dropped_off_user = user


class Bus(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool = False,
                 activities: VehicleActivity | None = None,
                 global_id: int = -1):
        super().__init__(node, capacity, mobility_service, is_personal, activities, global_id)



class Tram(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool = False,
                 activities: VehicleActivity | None = None,
                 global_id: int = -1):
        super().__init__(node, capacity, mobility_service, is_personal, activities, global_id)


class Metro(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool = False,
                 activities: VehicleActivity | None = None,
                 global_id: int = -1):
        super().__init__(node, capacity, mobility_service, is_personal, activities, global_id)


class Bike(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool,
                 activities: VehicleActivity | None = None,
                 global_id: int = -1):
        super().__init__(node, capacity, mobility_service, is_personal, activities, global_id)


class Train(Vehicle):
    def __init__(self,
                 node: str,
                 capacity: int,
                 mobility_service: str,
                 is_personal: bool = False,
                 activities: VehicleActivity | None = None,
                 global_id: int = -1):
        super().__init__(node, capacity, mobility_service, is_personal, activities, global_id)
