try:
    from apscheduler.schedulers.background import BackgroundScheduler
    _scheduler = BackgroundScheduler()
    _SCHEDULER_OK = True
except ImportError:
    _scheduler = None
    _SCHEDULER_OK = False
    print("[Startup] apscheduler not installed — callback scheduling disabled. Run: pip install apscheduler")

interview_store: dict = {}
batch_store:     dict = {}
opening_store:   dict = {}

DEFAULT_QUESTIONS = [
    "Tell me a bit about yourself and what brought you to apply for this role.",
    "What do you know about this position and why does it interest you?",
    "Can you walk me through a situation where you had to handle pressure or a tight deadline?",
    "Tell me about an achievement from your recent work that you're proud of.",
    "How do you prefer to communicate and collaborate with your team?",
    "Where do you see yourself growing in the next couple of years?",
]
