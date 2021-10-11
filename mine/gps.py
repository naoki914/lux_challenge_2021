from enum import Enum
import math
from typing import List
import math

from lux.constants import Constants
from lux.game_objects import Unit
from lux.game_map import Cell, GameMap, Position
from lux.game_constants import GAME_CONSTANTS


from utils import get_logger
logging = get_logger('gps', 'gps.log')

DIRECTIONS = Constants.DIRECTIONS

class ObjectiveActions(Enum):
    GATHER= 'g'
    BUILD= 'b'
    DEPOSIT= 'd'
    MOVE= 'm'


class GPS(GameMap):
    def __init__(self, map: GameMap, units: List[Unit]):
        self.height = map.height
        self.width = map.width
        self.map = map.map.copy()

        self.units = units

    @property
    def tiles(self):
        tiles = {
            'wood':[],
            'coal':[],
            'uranium':[],
            'empty':[],
            'road':[],
            'city':[]
        }
        for cell_row in self.map:
            for cell in cell_row:
                if cell.has_resource():
                    type = cell.resource.type
                    tiles[type].append(cell) 
                elif cell.citytile:
                    tiles['city'].append(cell)
                elif cell.road:
                    tiles['road'].append(cell)
                else:
                    tiles['empty'].append(cell)
                
        return tiles

    def update(self, map:GameMap, units:List[Unit]):
        self.units = units
        self.map = map.map

    def has_worker(self, pos:Position):
        for unit in self.units:
            if unit.pos == pos:
                return True
        return False

    def get_cell_type(self, cell: Cell):
        if cell.has_resource():
            return cell.resource.type

        if cell.citytile:
            # logging.info(f"citytile -> {cell.citytile}")
            return 'city'
        if cell.road:
            return 'road'

        return 'empty'
        
    def get_tiles(
            self
            ):
        """ Get map tiles """

        tiles = {
            
        }
        for cell_row in self.map:
            for cell in cell_row:
                if cell.has_resource():
                    type = cell.resource.type
                    tiles[type].append(cell) 
                elif cell.citytile:
                    tiles['city'].append(cell)
                elif cell.road:
                    tiles['road'].append(cell)
                else:
                    tiles['empty'].append(cell)
                
        return tiles

    def get_resource_tiles(self, wood=False, coal=False, uranium=False):
        tiles = self.tiles

        result = []
        if wood:
            result += tiles['wood']
        if coal:
            result += tiles['coal']
        if uranium:
            result += tiles['uranium']

        if result == []:
            result = tiles['wood'] + tiles['coal'] + tiles['uranium']

        return result

    
    def get_closest_resource_tiles(self, pos, wood=False, coal=False, uranium=False):
        tiles = self.get_resource_tiles(wood, coal, uranium)
        closest = self.get_closest_tile(pos, tiles)
        return closest

    def get_closest_city(self, team, pos):
        tiles = self.tiles['city']

        for tile in tiles:
            if tile.citytile != team:
                tiles.remove(tile)
        
        return self.get_closest_tile(pos, tiles)
                
    def get_closest_empy(self, pos):
        tiles = self.tiles['empty']
        
        return self.get_closest_tile(pos, tiles)
                


    def get_closest_tile(self, pos: Position, tiles: List[Cell]):
        """  """
        
        closest_dist = math.inf
        closest_tile = None
        current = None
        for tile in tiles:
            # logging.info(f"{str(tile.pos)} - {vars(tile)}")
            if tile.pos == pos: current = tile
            dist = tile.pos.distance_to(pos)
            if dist < closest_dist:
                closest_dist = dist
                closest_tile = tile
        return closest_tile or current

    def non_coliding_direction(self, cur: Position, target: Position):
        available_dirs = {
            DIRECTIONS.NORTH,
            DIRECTIONS.EAST,
            DIRECTIONS.SOUTH,
            DIRECTIONS.WEST,
        }

        dir = DIRECTIONS.CENTER
        
        closest_dist = cur.distance_to(target)
        for direction in available_dirs:
            newpos = cur.translate(direction, 1)
            dist = target.distance_to(newpos)
            if dist < closest_dist:
                # logger.info(f"{direction}- {closest_dist}| Current: {cur}, Next: {newpos}, Target: {target}")
                closest_dist= dist
                if not self.has_worker(newpos):
                    dir=direction

        return dir