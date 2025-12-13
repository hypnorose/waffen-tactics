from waffen_tactics.models.player import PlayerProfile

class ProgressionService:
    def __init__(self):
        pass

    def award_post_combat(self, player: PlayerProfile, won: bool):
        player.rounds += 1
        if won:
            player.wins += 1
            player.gold += 5
        else:
            player.gold += 2
        player.xp += 2

    def can_level_up(self, player: PlayerProfile, xp_needed: int) -> bool:
        return player.gold >= xp_needed

    def level_up(self, player: PlayerProfile, xp_needed: int):
        if self.can_level_up(player, xp_needed):
            player.gold -= xp_needed
            player.level += 1
            player.xp = 0
