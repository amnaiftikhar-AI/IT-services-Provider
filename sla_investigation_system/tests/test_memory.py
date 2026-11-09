def test_history_is_ticket_scoped():
    from app.memory.chat_memory import get_history
    class Query:
        def filter(self, condition):
            return self
        def order_by(self, condition):
            return self
        def all(self):
            return [
                type("Message", (), {"role": "user", "message": "Question for ticket A"})(),
                type("Message", (), {"role": "assistant", "message": "Answer for ticket A"})()
            ]
    class DB:
        def query(self, model):
            return Query()
    history = get_history(DB(), 1)
    assert all("ticket B" not in item["content"] for item in history)
