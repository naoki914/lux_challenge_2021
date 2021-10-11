import math, sys
from typing import Dict, List

from lux.game import Game
from lux.game_objects import City, Unit, Player
from lux.game_map import Cell, Position, GameMap, RESOURCE_TYPES
from lux.constants import Constants
from lux.game_constants import GAME_CONSTANTS
from lux import annotate

from mine.manager import Agent, Manager

# import logging
# logging.basicConfig(
#     filename="logs/gobal.log",
#     level=logging.INFO, 
#     filemode="w",
#     format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S')

from utils import get_logger
logging = get_logger('agent', 'agent.log')

DIRECTIONS = Constants.DIRECTIONS
game_state = None
my_agent = Agent()
manager = Manager()
tile_map = {
        'wood':[],
        'coal':[],
        'uranium':[],
        'empty':[],
        'road':[],
        'city':[]
    }
research_state = 0


def get_good_tiles() -> List[Cell]:
    """ Return a list of Cells corresponding to the resources in the map"""
    empty_tiles, resource_tiles = [], []
    for y in range(game_state.map.height):
        for x in range(game_state.map.width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)
            if not cell.citytile:
                empty_tiles.append(cell)
    return (empty_tiles, resource_tiles)

def get_tiles():
    """Return a map to the different types of tiles in the map."""
    # tile_map = {
    #     'wood':[],
    #     'coal':[],
    #     'uranium':[],
    #     'empty':[],
    #     'road':[],
    #     'city':[]
    # }
    for cell_rows in game_state.map.map:
        for cell in cell_rows:
            if cell.has_resource():
                type = cell.resource.type
                tile_map[type].append(cell) 
            elif cell.citytile:
                tile_map['city'].append(cell)
            elif cell.road:
                tile_map['road'].append(cell)
            else:
                tile_map['empty'].append(cell)

    return tile_map

def get_resource_tiles():
    result = tile_map['wood']

    if research_state >=1:
        result += tile_map['coal']
    if research_state >=2:
        result += tile_map['uranium']

    return result

def get_closest_tile(tiles: List[Cell], position: Position):
    closest_dist = math.inf
    closest_resource_tile = None
    for tile in tiles:
        dist = tile.pos.distance_to(position)
        if dist < closest_dist:
            closest_dist = dist
            closest_resource_tile = tile
    return closest_resource_tile

def unit_turn(player, unit):
    global game_state
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

def city_turn(city:City, player:Player):
    actions = []
    for city_tile in city.citytiles:

        if len(player.units) < player.city_tile_count:
            actions.append(city_tile.build_worker())
        if not city_tile.cooldown:
            actions.append(city_tile.research())

    return actions

def cities_handler(cities: Dict[str, City]) -> List[str]:
    actions = []
    for city in cities.values(): 
        for city_tile in city.citytiles:
            if not city_tile.cooldown:
                continue
                actions.append(city_tile.research())
    return actions

def agent(observation, configuration):
    global game_state
    global tile_map
    global my_agent

    turn = observation["step"]
    logging.info(f"{turn}")
    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])
    
    actions = []
    ### AI Code goes down here! ### 

    player = game_state.players[observation.player]
    
    manager.update(player, game_state.map, turn)


    actions += manager.get_worker_actions()
    # my_agent.update_workers(player.units)
    # tiles = get_tiles()
    # my_agent.update_state(game_state.map, player)
    
    # logging.info(vars(player))
    # opponent = game_state.players[(observation.player + 1) % 2]
    # width, height = game_state.map.width, game_state.map.height

    # resource_tiles = tiles['wood'] + tiles['coal'] + tiles['uranium']
    # empty_tiles, resource_tiles = get_good_tiles()
    # for y in range(height):
    #     for x in range(width):
    #         cell = game_state.map.get_cell(x, y)
    #         if cell.has_resource():
    #             resource_tiles.append(cell)


    # for city in player.cities.values():
    #     actions += city_turn(city, player)

    # we iterate over all our units and do something with them
    # for unit in player.units:
    #     job = my_agent.get_worker_job(unit.id)
    #     actions += job(unit)
        # actions += my_agent.get_worker_job(unit.id) #unit_turn(player, unit)
        # for city in player.cities:
        #     for city_tile in city.citytiles: 
        #         city_tile.build_worker()
        # if unit.can_build(game_state.map):
        # actions.append(unit.build_city())

        
    # you can add debug annotations using the functions in the annotate object
    actions.append(annotate.circle(0, 0))
    
    return actions
