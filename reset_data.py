"""
reset_data.py
-------------
Utility script to clear all stored data (users, vehicles, rentals) from the local data.pkl file.

This script is designed for development and testing purposes.
It resets the in-memory Store instance to an empty state, then saves it back to disk.

Usage:
    $ python reset_data.py

After running this script, you can repopulate sample data by executing:
    $ python seeds.py
"""

from app.models.store import Store


def main():
    """
    Clear all data (users, vehicles, rentals) from the persistent store.

    This function retrieves the singleton Store instance,
    removes all data entries, and saves the empty store back to `data.pkl`.
    """
    # Get the global Store instance (singleton)
    store = Store.instance()

    # Clear all existing data categories
    store.users.clear()
    store.vehicles.clear()
    store.rentals.clear()

    # Persist the cleared state to disk
    store.save()

    print("✅ data.pkl has been successfully cleared.")
    print("💡 Tip: Run `python seeds.py` to regenerate demo data.")


if __name__ == "__main__":
    main()
