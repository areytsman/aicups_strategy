from core.base_strategy import BaseStrategy
from functools import reduce
from datetime import datetime


class Strategy(BaseStrategy):
    tick = 0
    passengers_will_be_on_floor_by_floor = {1: {}, 2: {}, 3: {}, 4: {}, 5: {}, 6: {}, 7: {}, 8: {}, 9: {}}
    passengers_will_be_on_floor_by_id = {}
    ticks_to_floor_on_stairway_up = 200
    ticks_to_floor_on_stairway_down = 100
    ticks_walking_on_floor = 500
    ticks_waiting_elevator = 500
    ticks_exiting_from_elevator = 40
    ticks_to_open_doors = 100
    ticks_to_close_doors = 100
    ticks_to_floor_empty_elevator = 50
    start_time = datetime.now()
    elevators_index_by_id = {}
    passenger_x_speed = 2

    def on_tick(self, my_elevators, my_passengers, enemy_elevators, enemy_passengers):
        passengers = my_passengers + enemy_passengers
        if self.tick == 0:
            i = 0
            for my_elevator in my_elevators:
                self.elevators_index_by_id[my_elevator.id] = i
                i += 1
            i = 0
            for en_elevator in enemy_elevators:
                self.elevators_index_by_id[en_elevator.id] = i
                i += 1
            i = 0
            for j in range(0, 2001, 20):
                self.passengers_will_be_on_floor_by_floor[1][i] = (j, j + self.ticks_waiting_elevator, my_passengers[0])
                self.passengers_will_be_on_floor_by_floor[1][i + 1] = (
                    j, j + self.ticks_waiting_elevator, enemy_passengers[0])
                i += 2

        def calc_stairway_ticks_to_floor(passenger):
            if passenger.y < passenger.dest_floor:
                ticks_to_floor = self.ticks_to_floor_on_stairway_up
            else:
                ticks_to_floor = self.ticks_to_floor_on_stairway_down
            return abs((passenger.dest_floor - passenger.y) * ticks_to_floor)

        def init_tick():
            self.tick += 1
            if self.tick % 72 == 0:
                print(str(datetime.now()) + '\t' + str(self.tick / 72) + '% done')

        def predictor():
            for p in passengers:
                if p.state in (1, 3) and p.id not in self.passengers_will_be_on_floor_by_floor[p.floor].keys():
                    self.passengers_will_be_on_floor_by_floor[p.floor][p.id] = (self.tick, self.tick + p.time_to_away, p)
                if p.state == 2 and p.id in self.passengers_will_be_on_floor_by_floor[p.floor].keys():
                    self.passengers_will_be_on_floor_by_floor[p.floor].pop(p.id)
                if p.state == 4 and p.id not in self.passengers_will_be_on_floor_by_floor[
                    p.dest_floor].keys() and p.dest_floor != 1:
                    returns = self.tick + calc_stairway_ticks_to_floor(p) + self.ticks_walking_on_floor + 1
                    self.passengers_will_be_on_floor_by_floor[p.dest_floor][p.id] = (
                        returns, returns + self.ticks_waiting_elevator, p)
                if p.state == 6 and p.id not in self.passengers_will_be_on_floor_by_floor[
                    p.dest_floor].keys() and p.dest_floor != 1:
                    returns = self.tick + self.ticks_exiting_from_elevator + self.ticks_walking_on_floor
                    self.passengers_will_be_on_floor_by_floor[p.dest_floor][p.id] = (
                        returns, returns + self.ticks_waiting_elevator, p)

        def calc_passengers_mass(elevator):
            if len(elevator.passengers) == 0:
                return 1
            passengers_mass = reduce(lambda x, y: x * y, [p.weight for p in elevator.passengers])
            if len(elevator.passengers) > 10:
                passengers_mass *= 1.1
            return passengers_mass

        def calc_ticks_to_delivery(elevator, destination_floor):
            from_floor = elevator.y
            distance = from_floor - destination_floor
            if distance < 0:
                passengers_mass = calc_passengers_mass(elevator)
            else:
                passengers_mass = self.ticks_to_floor_empty_elevator
            if distance == 0:
                return 1
            if elevator.state in (3, 4):
                ticks_for_delivery = self.ticks_to_close_doors + passengers_mass * abs(distance) + \
                                     self.ticks_to_open_doors
                return ticks_for_delivery
            else:
                ticks_for_delivery = passengers_mass * abs(distance) + self.ticks_to_open_doors
                return ticks_for_delivery

        def get_elevator_x(elevator):
            if elevator.type == 'FIRST_PLAYER':
                return -1 * (40 + 80 * self.elevators_index_by_id[elevator.id])
            return 40 + 80 * self.elevators_index_by_id[elevator.id]

        def calc_ticks_to_elevator(passenger, elevator):
            return (passenger.x - get_elevator_x(elevator)) / self.passenger_x_speed

        def find_passengers_will_be_on_floor_on_tick(floor, tick):
            result = []
            for pid in self.passengers_will_be_on_floor_by_floor[floor].keys():
                if self.passengers_will_be_on_floor_by_floor[floor][pid][0] <= tick and \
                                self.passengers_will_be_on_floor_by_floor[floor][pid][1] > tick:
                    result.append(self.passengers_will_be_on_floor_by_floor[floor][pid][2])
            to_delete = []
            free_space = 0
            for elevator in my_elevators + enemy_elevators:
                if elevator.state in (0, 1) and elevator.next_floor == floor:
                    be_on_tick = calc_ticks_to_delivery(elevator, floor)
                    if be_on_tick < tick:
                        to_delete += find_passengers_will_be_on_floor_on_tick(floor, be_on_tick)
                        free_space += 20 - len(elevator.passengers) - len(
                            [p for p in elevator.passengers if p.dest_floor == floor])
            for p in to_delete[:free_space]:
                if p in result:
                    result.remove(p)
            return result

        def find_best_floor_to_go(elevator):
            floors_score = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}
            ticks_to_floors = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0}
            passengers_will_be_on_floor = {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: [], 9: []}
            passenger_going_time = int(abs(get_elevator_x(elevator) / self.passenger_x_speed))
            for floor in range(1, 10):
                if floor == elevator.floor:
                    floors_score[floor] = 0
                    continue
                ticks_to_floors[floor] = calc_ticks_to_delivery(elevator, floor)
                if self.tick + ticks_to_floors[floor] >= 7200:
                    floors_score[floor] = 0
                    continue
                passengers_will_be_on_floor[floor] = list(set(find_passengers_will_be_on_floor_on_tick(floor,
                                                                                                       self.tick +
                                                                                                       ticks_to_floors[
                                                                                                           floor] + passenger_going_time) + find_passengers_will_be_on_floor_on_tick(
                    floor, self.tick + ticks_to_floors[floor] + passenger_going_time + 200)))
                passengers_going_to_floor = [p for p in elevator.passengers if
                                             p.dest_floor == floor and p.dest_floor != elevator.floor]
                space_in_elevator = 20 - len(elevator.passengers) + len(passengers_going_to_floor)
                for p in passengers_going_to_floor:
                    if p.type == my_elevators[0].type:
                        floor_score = 10
                    else:
                        floor_score = 20
                    floors_score[floor] += floor_score / ticks_to_floors[floor]
                if self.tick + ticks_to_floors[floor] < 6600:
                    floor_score = 0
                    for p in passengers_will_be_on_floor[floor][:space_in_elevator]:
                        if p.type == my_elevators[0].type:
                            floor_score += 20
                        else:
                            floor_score += 40
                    for el in my_elevators + enemy_elevators:
                        if el.state in (1, 4) and el.next_floor == floor and el.next_floor != 1:
                            if calc_ticks_to_delivery(el, floor) < ticks_to_floors[floor]:
                                floor_score = 0
                        if el.state == 3 and el.floor == floor:
                            if el.type == my_elevators[0].type:
                                floor_score /= 2
                            elif self.elevators_index_by_id[el.id] >= self.elevators_index_by_id[elevator.id]:
                                floor_score /= 2
                            else:
                                floor_score /= 5
                    # if 4400 < self.tick < 6600:
                    #    floor_score *= 2
                    floors_score[floor] += floor_score / ticks_to_floors[floor]
            if self.tick < 6700:
                for en_el in enemy_elevators:
                    if en_el.state in (1, 4):
                        if calc_ticks_to_delivery(en_el, en_el.next_floor) > calc_ticks_to_delivery(elevator,
                                                                                                    en_el.next_floor) and len(
                            passengers_will_be_on_floor[en_el.next_floor]) > 2:
                            floors_score[en_el.next_floor] *= 1.5
            floors_score_list = list(floors_score.items())
            floors_score_list.sort(key=lambda x: x[1], reverse=True)
            best_floor = floors_score_list[0][0]
            if floors_score_list[0][1] == floors_score_list[1][1]:
                if ticks_to_floors[floors_score_list[0][0]] > ticks_to_floors[floors_score_list[1][0]]:
                    best_floor = floors_score_list[1][0]
            return best_floor

        def set_passengers_to_elevator(elevator):
            if self.tick <= 2000 and elevator.floor == 1:
                start_elevators_strategy()
                return
            elevators_on_floor = [el for el in my_elevators if el.floor == elevator.floor and el.state == 3]
            closest = elevator
            if len(elevators_on_floor) > 1:
                for el in elevators_on_floor:
                    if self.elevators_index_by_id[el.id] < self.elevators_index_by_id[closest.id]:
                        closest = el
                if closest == elevator:
                    passengers_to_set = [p for p in passengers if
                                         p.state in (1, 3) and p.floor == elevator.floor and abs(
                                             p.dest_floor - p.from_floor) > 2]
                    passengers_to_set.sort(key=lambda x: abs(x.dest_floor - x.from_floor), reverse=True)
                    for pas in passengers_to_set[:20 - len(elevator.passengers)]:
                        pas.set_elevator(elevator)
                        return
            passengers_to_set = [p for p in passengers if
                                 p.state in (1, 3) and p.floor == elevator.floor and abs(
                                     p.dest_floor - p.from_floor) > 1]
            passengers_to_set.sort(key=lambda x: abs(x.dest_floor - x.from_floor), reverse=True)
            for pas in passengers_to_set[:20 - len(elevator.passengers)]:
                pas.set_elevator(elevator)

        def count_valid_elevator_passengers_on_floor(elevator):
            count = 0
            for p in my_passengers + enemy_passengers:
                if p.floor == elevator.floor and abs(p.dest_floor - p.from_floor) > 1:
                    if p.state < 4:
                        if calc_ticks_to_elevator(p, elevator) >= p.time_to_away:
                            continue
                        if p.state in (1, 3):
                            count += 1
                        if p.state == 2:
                            if p.elevator == elevator.id:
                                count += 1
            another_enemy_elevators_on_floor = [el for el in enemy_elevators if
                                                el.floor == elevator.floor and el.state == 3]
            if len(another_enemy_elevators_on_floor) > 0:
                enemy_free_space = 0
                for el in another_enemy_elevators_on_floor:
                    if self.elevators_index_by_id[el.id] < self.elevators_index_by_id[elevator.id]:
                        enemy_free_space += 20 - len(el.passengers)
                passengers_going_to_enemy = [p for p in passengers if
                                             p.floor == elevator.floor and p.state == 2 and p.elevator in [eid.id for
                                                                                                           eid in
                                                                                                           enemy_elevators]]
                if len(passengers_going_to_enemy) > enemy_free_space:
                    count += len(passengers_going_to_enemy) - enemy_free_space
            return count

        def start_elevators_strategy():
            for pas in [p for p in passengers if p.state in (1, 3) and p.dest_floor >= 7 and p.floor == 1]:
                if pas.dest_floor >= 8:
                    pas.set_elevator(my_elevators[0])
                pas.set_elevator(my_elevators[1])

            for pas in [p for p in passengers if p.state in (1, 3) and p.dest_floor >= 4 and p.floor == 1]:
                if pas.dest_floor >= 5:
                    pas.set_elevator(my_elevators[2])
                pas.set_elevator(my_elevators[3])

        def is_need_wait(elevator):
            if len(elevator.passengers) >= 20:
                return False
            if self.tick <= 2000:
                return True
            if self.tick > 6600 and len(elevator.passengers) >= 15:
                return False
            passenger_going_time = int(abs(get_elevator_x(elevator) / self.passenger_x_speed))
            num_valid_passengers = count_valid_elevator_passengers_on_floor(elevator)
            free_space = 20 - len(elevator.passengers)
            future_passengers100 = find_passengers_will_be_on_floor_on_tick(elevator.floor,
                                                                            self.tick + 100 + passenger_going_time)
            future_passengers250 = find_passengers_will_be_on_floor_on_tick(elevator.floor,
                                                                            self.tick + 250 + passenger_going_time)
            future_passengers500 = find_passengers_will_be_on_floor_on_tick(elevator.floor,
                                                                            self.tick + 500 + passenger_going_time)
            if num_valid_passengers == 0:
                if self.tick > 6600 and len(elevator.passengers) >= 10:
                    return False
                if len(future_passengers100) > 1 or (len(future_passengers250) > 3 and free_space > 2) or (
                                len(future_passengers500) > 10 and free_space > 4):
                    if len([el for el in enemy_elevators if
                            self.elevators_index_by_id[el.id] < self.elevators_index_by_id[
                                elevator.id] and el.state == 3 and el.floor == elevator.floor and el.time_on_floor > 150]) == 0:
                        return True
                    else:
                        return False
                else:
                    return False
            if len([p for p in passengers if p.state == 2 and p.elevator == elevator.id]) > 0:
                return True
            enemy_elevators_on_floor = [el for el in enemy_elevators if
                                        el.floor == elevator.floor and el.state == 3]
            enemy_elevators_free_space = 0
            for el in enemy_elevators_on_floor:
                if self.elevators_index_by_id[el.id] < self.elevators_index_by_id[elevator.id]:
                    enemy_elevators_free_space += 20 - len(el.passengers)
            if len(enemy_elevators_on_floor) > 0 and self.tick > 2000:
                if enemy_elevators_free_space >= num_valid_passengers + len(future_passengers100):
                    return False
            another_my_elevators_on_floor = [el for el in my_elevators if
                                             el.floor == elevator.floor and el.state == 3 and el != elevator]
            if len(another_my_elevators_on_floor) > 0:
                # another_my_elevators_on_floor.sort(key=lambda x: 20 - len(x.passengers))
                another_els_free_space = 0
                for el in another_my_elevators_on_floor:
                    if self.elevators_index_by_id[el.id] < self.elevators_index_by_id[elevator.id]:
                        another_els_free_space += 20 - len(el.passengers)
                if another_els_free_space >= num_valid_passengers + len(future_passengers100):
                    return False
            return True

        def main_elevators_strategy():
            for elevator in my_elevators:
                if elevator.time_on_floor <= 140:
                    set_passengers_to_elevator(elevator)
                    continue
                if elevator.state == 3 and elevator.time_on_floor > 140:
                    if not is_need_wait(elevator):
                        elevator.go_to_floor(find_best_floor_to_go(elevator))
                    else:
                        set_passengers_to_elevator(elevator)

        def finally_work():
            for floor in range(1, 10):
                to_delete = []
                for pid in self.passengers_will_be_on_floor_by_floor[floor].keys():
                    if self.passengers_will_be_on_floor_by_floor[floor][pid][1] < self.tick:
                        to_delete.append(pid)
                for pid in to_delete:
                    self.passengers_will_be_on_floor_by_floor[floor].pop(pid)

        try:
            init_tick()
            predictor()
            main_elevators_strategy()
            finally_work()
            if self.tick == 7200:
                print(my_elevators[0].type)
                print(datetime.now() - self.start_time)
        except Exception as e:
            print(e)
