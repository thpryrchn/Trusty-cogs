from dataclasses import dataclass

@dataclass
class TeamEntry:
    game_state: str
    team_name: str
    period: int
    channel: list
    goal_id: dict
    created_channel: list
    game_start: str

    def to_json(self) -> dict:
        return {
            "team_name": self.team_name,
            "game_state": self.game_state,
            "channel": self.channel,
            "period": self.period,
            "created_channel": self.created_channel,
            "game_start": self.game_start,
            "goal_id": self.goal_id,
        }

    @classmethod
    def from_json(cls, data: dict):
        return cls(
            data["team_name"],
            data["game_state"],
            data["game_start"],
            data["channel"],
            data["period"],
            data["goal_id"],
            data["created_channel"],
        )
