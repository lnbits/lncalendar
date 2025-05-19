async def m001_initial(db):
    """
    Initial schedules table.
    """
    await db.execute(
        f"""
        CREATE TABLE lncalendar.schedule (
            id TEXT PRIMARY KEY,
            wallet TEXT NOT NULL,
            name TEXT NOT NULL,
            start_day INTEGER NOT NULL,
            end_day INTEGER NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            amount {db.big_int} NOT NULL
        );
    """
    )

    """
    Initial unavailability table.
    This is used for the user to set unavailable times.
    """
    await db.execute(
        f"""
        CREATE TABLE lncalendar.unavailable (
            id TEXT PRIMARY KEY,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            schedule TEXT NOT NULL,
            time TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )

    """
    Initial appointments table.
    """
    await db.execute(
        f"""
        CREATE TABLE lncalendar.appointment (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT,
            info TEXT,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            schedule TEXT NOT NULL,
            paid BOOLEAN DEFAULT false,
            time TIMESTAMP NOT NULL DEFAULT {db.timestamp_now}
        );
    """
    )


async def m002_add_extra_column_to_scheduler(db):
    """
    Adds extra to scheduler.
    """
    await db.execute("ALTER TABLE lncalendar.schedule ADD COLUMN extra TEXT")


async def m003_add_extra_column_to_appointment(db):
    """
    Adds extra to appointment.
    """
    await db.execute("ALTER TABLE lncalendar.appointment ADD COLUMN extra TEXT")
