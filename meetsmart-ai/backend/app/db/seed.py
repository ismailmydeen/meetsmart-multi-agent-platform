"""
Run once to create tables and populate sample employees + busy slots.
Usage: python -m app.db.seed
"""
from datetime import datetime, timedelta
from ..database import Base, engine, SessionLocal
from ..models import Employee, ScheduleSlot


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Employee).count() > 0:
        print("Already seeded, skipping.")
        db.close()
        return

    employees = [
        Employee(name="Ismail", email="ismail@thinkpalm.com", track="QA"),
        Employee(name="Aneesh K.S.", email="aneesh.ks@thinkpalm.com", track="Lead"),
        Employee(name="Priya", email="priya@thinkpalm.com", track="Backend"),
        Employee(name="Rahul", email="rahul@thinkpalm.com", track="Frontend"),
    ]
    db.add_all(employees)
    db.commit()
    for e in employees:
        db.refresh(e)

    today = datetime.now().date()
    tomorrow = datetime.combine(today + timedelta(days=1), datetime.min.time())

    busy_slots = [
        # Ismail busy 10-11
        ScheduleSlot(employee_id=employees[0].id, start_time=tomorrow.replace(hour=10), end_time=tomorrow.replace(hour=11), title="Standup"),
        # Aneesh busy 9:30-10:30 and 14-15
        ScheduleSlot(employee_id=employees[1].id, start_time=tomorrow.replace(hour=9, minute=30), end_time=tomorrow.replace(hour=10, minute=30), title="Review"),
        ScheduleSlot(employee_id=employees[1].id, start_time=tomorrow.replace(hour=14), end_time=tomorrow.replace(hour=15), title="1:1"),
        # Priya busy 11-12
        ScheduleSlot(employee_id=employees[2].id, start_time=tomorrow.replace(hour=11), end_time=tomorrow.replace(hour=12), title="Sprint planning"),
    ]
    db.add_all(busy_slots)
    db.commit()
    db.close()
    print("Seeded 4 employees and sample busy slots for", tomorrow.date())


if __name__ == "__main__":
    run()
