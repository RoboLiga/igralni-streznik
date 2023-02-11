import logging

from src.utils import check_if_object_in_area
from src.servers.GameServer import GameServer


class Orchard(GameServer):
    def __init__(self, state_server, game_config, team_1, team_2):
        GameServer.__init__(self, state_server, game_config, team_1, team_2)

        self.logger = logging.getLogger('games.Orchard')

        # Hive zones is used to keep track in which zones the hives have been.
        self.hive_zones = {}
        for hive_id in game_config['objects']['healthy_hives'] + game_config['objects']['diseased_hives']:
            self.hive_zones[hive_id] = set()

        self.secures_hives = set()

        self.team_1_healthy_hives_score = 0
        self.team_2_healthy_hives_score = 0

    def compute_score(self):
        """
        Computes score for each team
        """

        # Count diseased hives
        team_1_diseased_count = 0
        team_2_diseased_count = 0

        # Check if hives positions, update hive_zones and score
        for healthy_hive in self.state_data.objects['healthy_hives'].values():

            if healthy_hive.id in self.secures_hives:
                continue

            if check_if_object_in_area(healthy_hive.position, self.state_data.fields['team_1_zone']):
                self.hive_zones[healthy_hive.id].add('team_1_zone')
            elif check_if_object_in_area(healthy_hive.position, self.state_data.fields['team_2_zone']):
                self.hive_zones[healthy_hive.id].add('team_2_zone')
            elif check_if_object_in_area(healthy_hive.position, self.state_data.fields['neutral_zone']):
                self.hive_zones[healthy_hive.id].add('neutral_zone')

            if check_if_object_in_area(healthy_hive.position, self.state_data.fields['team_1_basket']):
                self.logger.debug("Healthy hive %s is in team 1 basket" % healthy_hive.id)
                self.secures_hives.add(healthy_hive.id)
                if 'team_2_zone' in self.hive_zones[healthy_hive.id]:
                    self.team_1_healthy_hives_score += self.state_data.config['points']['enemy']
                elif 'neutral_zone' in self.hive_zones[healthy_hive.id]:
                    self.team_1_healthy_hives_score += self.state_data.config['points']['neutral']
                else:
                    self.team_1_healthy_hives_score += self.state_data.config['points']['home']

            if check_if_object_in_area(healthy_hive.position, self.state_data.fields['team_2_basket']):
                self.logger.debug("Healthy hive %s is in team 2 basket" % healthy_hive.id)
                self.secures_hives.add(healthy_hive.id)

                if 'team_1_zone' in self.hive_zones[healthy_hive.id]:
                    self.team_1_healthy_hives_score += self.state_data.config['points']['enemy']
                elif 'neutral_zone' in self.hive_zones[healthy_hive.id]:
                    self.team_1_healthy_hives_score += self.state_data.config['points']['neutral']
                else:
                    self.team_1_healthy_hives_score += self.state_data.config['points']['home']

        for diseased_hive in self.state_data.objects['diseased_hives'].values():
            if check_if_object_in_area(diseased_hive.position, self.state_data.fields['team_1_zone']):
                team_1_diseased_count += 1
            elif check_if_object_in_area(diseased_hive.position, self.state_data.fields['team_2_zone']):
                team_2_diseased_count += 1

        self.team_1.score = self.team_1_healthy_hives_score + \
                            team_1_diseased_count * self.state_data.config['points']['diseased']
        self.team_2.score = self.team_2_healthy_hives_score + \
                            team_2_diseased_count * self.state_data.config['points']['diseased']
