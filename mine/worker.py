from enum import Enum
from typing import List

from lux.game_objects import Unit
from lux.game_map import Cell, Position
from lux.game_constants import GAME_CONSTANTS

from utils import get_logger
logging = get_logger('worker', 'worker.log')


class ObjectiveActions(Enum):
    GATHER= 'g'
    BUILD= 'b'
    DEPOSIT= 'd'


class Objective:
    def __init__(self, pos: Position, action: str):
        self.pos = pos
        self.action = action

    @classmethod
    def go_gather(cls, pos: Position):
        return cls(pos, ObjectiveActions.GATHER)
    
    @classmethod
    def go_build(cls, pos: Position):
        return cls(pos, ObjectiveActions.BUILD)
    
    @classmethod
    def go_deposit_closest(cls, pos: Position):
        return cls(pos, ObjectiveActions.DEPOSIT)
    
    def __str__(self) -> str:
        return f"{self.action} -> {self.pos}"
    
    def __repr__(self) -> str:
        return f"{self.action} -> {str(self.pos)}"

class Worker(Unit):
    def __init__(self, unit: Unit, cell: Cell, turn):
        # Not Changeable
        self.team = unit.team
        self.id = unit.id
        self.type = unit.type
        
        # Changeable
        self.pos = unit.pos
        self.cell = cell
        self.cooldown = unit.cooldown
        self.cargo = unit.cargo

        #own
        self.objective = None
        self.role = None
        self.turn = turn

    def __eq__(self, other: Unit):
        return self.id == other.id

    def get_cargo(self) -> int:
        return self.cargo.wood + self.cargo.coal + self.cargo.uranium

    def update_worker(self, unit: Unit, cell: Cell, turn) -> None:
        self.pos = unit.pos
        self.cell = cell
        self.cooldown = unit.cooldown
        self.cargo = unit.cargo

        self.turn = turn
        self.check_objective()

        return self

    def check_objective(self) -> None:
        if not self.objective: return

        if self.objective.action == ObjectiveActions.GATHER:
            self.check_gather_objective()

        elif self.objective.action == ObjectiveActions.BUILD:
            self.check_build_objective()

        else: # default is DEPOSIT
            self.check_deposit_objective()

    def get_step(self):
        if self.get_cargo_space_left():
            return ObjectiveActions.GATHER
        elif self.role == 'b':
            return ObjectiveActions.BUILD
        else:
            return ObjectiveActions.DEPOSIT
        
    def check_deposit_objective(self) -> None:
        if not self.at_objective(): return
        if self.get_cargo == 0:
            self.objective = None

    def check_build_objective(self) -> None:
        if not self.at_objective(): return
        if not self.can_build():
            self.objective = None

    def check_gather_objective(self) -> None:
        if not self.at_objective(): return
        if self.get_cargo_space_left() == 0:
            self.objective = None
    
    def set_objective(self, pos: Position, action:str) -> None:
        self.objective = Objective(pos, action)
        logging.info(f"New Objective! {self.id} ({self.get_cargo()}) -> {self.objective}")

    def can_build(self) -> bool:
        if not self.cell.has_resource() and self.can_act() and (self.cargo.wood + self.cargo.coal + self.cargo.uranium) >= GAME_CONSTANTS["PARAMETERS"]["CITY_BUILD_COST"]:
            return True
        return False

    def at_objective(self):
        if self.objective.action == ObjectiveActions.GATHER:
            if self.role =='b' and self.cell.citytile:
                return False
            return self.objective.pos - self.pos <= 1
        
        return self.pos == self.objective.pos

    def get_action(self) -> List[str]:
        logging.info(f"{self.turn} | {self.id}: {self.objective}")
        if not self.objective:
            return []
        else:
            if not self.can_act: return []
            if self.objective.action == ObjectiveActions.GATHER:
                return self.get_move_action()

            elif self.objective.action == ObjectiveActions.BUILD:
                return self.build_city()

            elif self.objective.action == ObjectiveActions.DEPOSIT:
                return self.get_move_action()

            else: # default is DEPOSIT
                return []
                

    def get_move_action(self):
        direction = self.pos.direction_to(self.objective.pos)
        return self.move(direction)

    def get_needed_cell(self):
        if self.objective.action == ObjectiveActions.GATHER:
            return 'resource'
        if self.objective.action == ObjectiveActions.BUILD:
            return 'empty'
        if self.objective.action == ObjectiveActions.DEPOSIT:
            return 'city'