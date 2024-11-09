"""
First module for run the program
"""

# Moduli standard
import asyncio
import importlib
import os
import sys

# Add the 'func' and 'class' directory to the system path to import custom modules
sys.path.append(os.path.join(os.path.dirname(__file__), "func"))
sys.path.append(os.path.join(os.path.dirname(__file__), "classes"))

PERSONAL_CHAT_ID = "me"
LOG_IN_PERSONAL_CHAT = True

root_dir = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    from func.utils import check_lock, acquire_lock, release_lock
    from func.config import load_configuration

    configuration = load_configuration()

    if configuration.disabled:
        print("Disabled")
        sys.exit(0)

    lock_file = configuration.lock_file

    check_lock(lock_file)
    acquire_lock(lock_file)

    main = importlib.import_module('func.main')
    try:
        asyncio.run(main.main())
    except Exception:
        release_lock(lock_file)
    finally:
        release_lock(lock_file)
