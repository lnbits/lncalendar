from sqlalchemy.exc import OperationalError


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


async def m002_rename_time_to_created_at(db):
    """
    Rename time to created_at in the unavailability table.
    """
    await db.execute(
        """
        ALTER TABLE lncalendar.unavailable
        RENAME COLUMN time TO created_at;
        """
    )
    await db.execute(
        """
        ALTER TABLE lncalendar.appointment
        RENAME COLUMN time TO created_at;
        """
    )

    """
    Add name to the unavailable table.
    """
    await db.execute(
        """
        ALTER TABLE lncalendar.unavailable
        ADD COLUMN name TEXT NOT NULL DEFAULT 'Unavailable';
        """
    )

    """
    Add timeslot to the schedule table.
    """
    await db.execute(
        """
        ALTER TABLE lncalendar.schedule
        ADD COLUMN timeslot INTEGER NOT NULL DEFAULT 30;
        """
    )

    """
    Add nostr_pubkey to the appointment table.
    """
    await db.execute(
        """
        ALTER TABLE lncalendar.appointment
        ADD COLUMN nostr_pubkey TEXT;
        """
    )


async def m003_add_fiat_currency(db):
    """
    Add currency to schedule to allow fiat denomination
    of appointments. Make price a float.
    """
    try:
        await db.execute(
            "ALTER TABLE lncalendar.schedule RENAME TO schedule_backup;")
        await db.execute(
            """
            CREATE TABLE lncalendar.schedule (
                id TEXT PRIMARY KEY,
                wallet TEXT NOT NULL,
                name TEXT NOT NULL,
                start_day INTEGER NOT NULL,
                end_day INTEGER NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                amount FLOAT NOT NULL,
                timeslot INTEGER NOT NULL DEFAULT 30,
                currency TEXT NOT NULL DEFAULT 'sat'
            );
        """
        )

        await db.execute(
            """
            INSERT INTO lncalendar.schedule (id, wallet, name, start_day, end_day, start_time, end_time, amount, timeslot) 
            SELECT id, wallet, name, start_day, end_day, start_time, end_time, amount, timeslot FROM lncalendar.schedule_backup;
            """
        )

        await db.execute("DROP TABLE lncalendar.schedule_backup;")
    except OperationalError:
        pass

async def m004_add_lncalendar_settings(db):
    """
    Add settings table to store global settings.
    """
    await db.execute(
        """
        CREATE TABLE lncalendar.settings (
            nostr_private_key TEXT NOT NULL,
            relays TEXT
        );
    """
    )

async def m005_add_public_key(db):
    """
    Add public_key to schedule table.
    """
    await db.execute(
        """
        ALTER TABLE lncalendar.schedule
        ADD COLUMN public_key TEXT;
        """
    )