from typing import Callable, Dict, List
from enum import Enum, auto
# logging.basicConfig(
#     filename="logs/agent.log",
#     level=logging.INFO, 
#     filemode="w",
#     format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S')
from utils import get_logger
logging = get_logger('manager', 'manager.log')
import math



from lux.game_objects import Player, Unit, City
from lux.game_map import Cell, GameMap, Position
from lux.game_constants import GAME_CONSTANTS

from .gps import GPS
from .worker import Worker, ObjectiveActions

STRAT_RATIO = 2

def is_closer(r1, r2, target):
    return abs(r1-target) < abs(r2-target)


class WorkerRoles(Enum):
    BUILDER= auto()
    GATHERER= auto()

class Manager(Player):

    def __init__(self):
        self.turn = 0
        self.team = None
        self.research_points = 0
        self.city_tile_count = 0
        self.gps = None
        self.workers = {}

        # self.gatherers = {}
        # self.builders = {}

    @property
    def gatherers(self):
        gatherers = {}
        for worker in self.workers.values():
            if worker.role == "g":
                gatherers[worker.id] = worker
        return gatherers

    @property
    def builders(self):
        builders = {}
        for worker in self.workers.values():
            if worker.role == "b":
                builders[worker.id] = worker
        return builders
    
    @property
    def role_ratio(self):
        return self.gatherers/self.builders

    def update(self, player:Player, map:GameMap, turn: int):
        # Get new state of game
        self.turn = turn
        self.update_gps(map, player.units)
        self.update_workers(player.units)

        # Plan next steps
        self.update_objectives()

    def update_gps(self, map, units):
        if self.gps:
            self.gps.update(map, units)
        else:
            self.gps = GPS(map, units)
        

    def update_workers(self, units):
        cur ={}
        for unit in units:
            if unit.id in self.workers:
                cur[unit.id] = self.workers[unit.id].update_worker(
                                                            unit, 
                                                            self.gps.get_cell_by_pos(
                                                                unit.pos
                                                            ),
                                                            self.turn
                                                        )

            else:
                cur[unit.id] = Worker(
                                    unit, 
                                    self.gps.get_cell_by_pos(
                                        unit.pos
                                    ),
                                    self.turn
                                )
        self.workers = cur

        self.update_roles()

        # logging.info(f"{self.turn} Updated Workers=> Gatherers: {list(self.gatherers.keys())} | Builders: {list(self.builders.keys())}")


    def update_roles(self):
        for worker in self.workers.values():
            if not self.builders:
                self.workers[worker.id].role = 'b'

            elif worker.role == None:
                self.workers[worker.id].role = self.get_needed_role()


    def get_needed_role(self):
        if not self.builders or self.ratio >= STRAT_RATIO:
            return "b"
        if not self.gatherers:
            return "g"





    def get_worker_actions(self):
        actions = []
        for worker in self.workers.values():
            objective = worker.objective
            if not worker.at_objective():
                dir =self.gps.non_coliding_direction(worker.pos, objective.pos)
                actions.append(worker.move(dir))
            else:
                if objective.action == ObjectiveActions.BUILD:
                    actions.append(worker.build_city())
            # cell = self.gps.non_coliding_direction(worker.pos, cell.pos)
        return actions

    def update_objectives(self):
        for w_id in self.workers:
            if not self.workers[w_id].objective: 
                step = self.workers[w_id].get_step()
                if step == ObjectiveActions.BUILD:
                    cell = self.gps.get_closest_empy(self.workers[w_id].pos)
                    logging.info(f"{w_id} ({self.workers[w_id].cargo}) wants to BUILD at {cell.pos} => {vars(cell)}")

                    self.workers[w_id].set_objective(cell.pos, ObjectiveActions.BUILD)

                elif step == ObjectiveActions.GATHER:
                    cell = self.gps.get_closest_resource_tiles(
                                                self.workers[w_id].pos, 
                                                wood=True, 
                                                coal = self.researched_coal(),
                                                uranium= self.researched_uranium()
                                            )
                    logging.info(f"{w_id} ({self.workers[w_id].cargo}) wants to GATHER at {cell.pos} => {vars(cell)}")
                    self.workers[w_id].set_objective(cell.pos, ObjectiveActions.GATHER)

                else:
                    cell = self.gps.get_closest_city(self.team, self.workers[w_id].pos)
                    logging.info(f"{w_id} ({self.workers[w_id].cargo}) wants to DEPOSIT at {cell.pos} => {vars(cell)}")
                    self.workers[w_id].set_objective(cell.pos, ObjectiveActions.DEPOSIT)
            
                

    

class Agent:
    ratio = 2 # ratio of gatherers to builders
    tile_map = {}
    research_state = 0
    units = []
    def __init__(self):
        self.workers = {
            WorkerRoles.BUILDER: [],
            WorkerRoles.GATHERER: []
        }

    @property
    def builders(self):
        return self.workers[WorkerRoles.BUILDER]
    
    @property
    def gatherers(self):
        return self.workers[WorkerRoles.GATHERER]


    def update_workers(self, units: List[Unit]):
        self.units = units
        for unit in units:
            if unit.id not in list(self.builders) + list(self.gatherers):
                self.add_worker(unit.id)

    def update_state(self, map:GameMap, player:Player):
        logging.info("Updating")
        self.map= GPS(map, self.units)
        self.research_state = player.research_points


    def add_worker(self, worker_id):
        if len(self.builders) == 0:
            logging.info(f"1st Adding BUILDER {worker_id}")
            self.workers[WorkerRoles.BUILDER].append(worker_id)
        elif len(self.gatherers) == 0 or is_closer(
                                            (len(self.builders)+1)/len(self.gatherers),
                                            len(self.builders)/(len(self.gatherers)+1),
                                            self.ratio
                                        ):
            logging.info(f"Adding GATHERER {worker_id}")
            self.workers[WorkerRoles.GATHERER].append(worker_id)
        else:
            logging.info(f"Adding BUILDER {worker_id}")
            self.workers[WorkerRoles.BUILDER].append(worker_id)

        logging.info(f"WORKER {self.workers}")

    def get_worker_job(self, worker_id) -> Callable:
        if (worker_id in self.workers[WorkerRoles.BUILDER] or 
            len(self.workers) + len(self.gatherers) <=1):
            return self.builder_job
        else:
            return self.gatherer_job

    def builder_job(self, unit: Unit):
        actions =[]

        if unit.get_cargo_space_left() == 0:
            resource_tile = self.map.get_closest_tile(unit.pos, "empty")
            if resource_tile.pos == unit.pos:
                actions.append(unit.build_city())
            else:    
                move_dir = self.get_move_dir(unit, resource_tile.pos)
                actions.append(unit.move(move_dir))

        else:
            resource_tile = self.map.get_closest_tile(unit.pos, "wood")
            if resource_tile is not None:
                actions.append(unit.move(self.get_move_dir(unit, resource_tile.pos)))

        return actions

    def gatherer_job(self, unit: Unit):
        actions =[]

        if unit.get_cargo_space_left() > 0:
            # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it
            resource_tile = get_closest_tile(get_resource_tiles(self.tile_map) ,unit.pos)
            if resource_tile is not None:
                actions.append(unit.move(self.get_move_dir(unit, resource_tile.pos)))
        else:
            closest_dist = math.inf
            closest_city_tile = None
            for city_tile in self.tile_map['city']:
                dist = city_tile.pos.distance_to(unit.pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_city_tile = city_tile
            if closest_city_tile is not None:
                move_dir = self.get_move_dir(unit, closest_city_tile.pos)
                actions.append(unit.move(move_dir))
            resource_tile = get_closest_tile(self.tile_map['empty'] ,unit.pos)
            if resource_tile.pos == unit.pos:
                actions.append(unit.build_city())
            else:    
                move_dir = self.get_move_dir(unit, resource_tile.pos)
                actions.append(unit.move(move_dir))

        return actions

    def get_move_dir(self, unit, pos):
        move_dir = self.map.non_coliding_direction(unit.pos, pos)
        return move_dir
    def closest_gather(self):
        pass

    
    def unit_turn(player, unit):
        global tile_map

        actions = []


        if unit.is_worker() and unit.can_act():
            # Decide what type of task collect/create city
            
            closest_dist = math.inf
            closest_resource_tile = None
            
            if unit.get_cargo_space_left() > 0:
                # if the unit is a worker and we have space in cargo, lets find the nearest resource tile and try to mine it
                resource_tile = get_closest_tile(get_resource_tiles() ,unit.pos)
                if resource_tile is not None:
                    actions.append(unit.move(unit.pos.direction_to(resource_tile.pos)))
            else:
                if len(player.units) >= player.city_tile_count:
                    # Create a city if worker number is capped
                    resource_tile = get_closest_tile(tile_map['empty'] ,unit.pos)
                    if resource_tile.pos == unit.pos:
                        actions.append(unit.build_city())
                    else:    
                        move_dir = unit.pos.direction_to(resource_tile.pos)
                        actions.append(unit.move(move_dir))



                # if unit is a worker and there is no cargo space left, and we have cities, lets return to them
                if len(player.cities) > 0:
                    closest_dist = math.inf
                    closest_city_tile = None
                    for k, city in player.cities.items():
                        for city_tile in city.citytiles:
                            dist = city_tile.pos.distance_to(unit.pos)
                            if dist < closest_dist:
                                closest_dist = dist
                                closest_city_tile = city_tile
                    if closest_city_tile is not None:
                        move_dir = unit.pos.direction_to(closest_city_tile.pos)
                        actions.append(unit.move(move_dir))
        for action in actions:
            logging.info(action)
        
        return actions