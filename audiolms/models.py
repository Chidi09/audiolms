# audiolms/models.py
# This file would typically define data models for your LMS,
# e.g., using SQLAlchemy or another ORM.
# For this demo, it remains a placeholder.

class AudioRecord:
    """
    Conceptual model for an audio recording in the LMS.
    In a real application, this would map to a database table.
    """
    def __init__(self, id: str, name: str, url: str, duration: float = 0.0):
        self.id = id
        self.name = name
        self.url = url
        self.duration = duration

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "duration": self.duration
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(data['id'], data['name'], data['url'], data.get('duration', 0.0))

# Example usage (not used in the current demo, but for illustration)
# def get_all_audio_records():
#     """Simulates fetching all audio records from a database."""
#     # In a real app, this would query your DB
#     return [
#         AudioRecord("1", "Lecture 1 Intro", "/static/audio/lecture1.mp3", 120.5),
#         AudioRecord("2", "Discussion on Chapter 3", "/static/audio/discussion.wav", 300.0)
#     ]
