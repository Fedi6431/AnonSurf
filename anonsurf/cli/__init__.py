from concurrent import futures
from .. import *
from ..controller.controller import Tor
from ..system_proxy import set_system_proxy
import argparse
import time

PROXY = Tor()
EXECUTOR = futures.ThreadPoolExecutor(50)
DESCRIPTION = """#==================Anonsurf 4 windows==================#
#   -h          |   Show all commands                  #
#   -start      |   Start tor services                 #
#   -stop       |   Stop tor services                  #
#   -restart    |   Restart tor services               #
#======================================================#"""

def start_cli():
    parser = argparse.ArgumentParser(DESCRIPTION)
    
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--start", help="Start tor services")
    group.add_argument("--stop", help="Stop tor services")
    group.add_argument("--restart", help="Restart tor services")

    args = parser.parse_args()

    if args.start:
        if not PROXY.running:
            print("Starting tor services...")
            EXECUTOR.submit(PROXY.start)
            print("From now every 10 seconds you'll get an update message")
            while PROXY.status_bootstrap < 100 and not PROXY.exception:
                print(f"PROXY STATUS PERCENTAGE: {PROXY.status_bootstrap}%")
                time.sleep(10)
            set_system_proxy(PROXY, enabled=True)
        else:
            print("Tor services are already running...")
    elif args.stop:
        if PROXY.running:
            print("Stopping tor services...")
            EXECUTOR.submit(PROXY.stop)
            set_system_proxy(PROXY, False)
        else:
            print("Tor services aren't running...")
    elif args.restart:
        print("Restarting the service...")
        EXECUTOR.submit(PROXY.stop)
        set_system_proxy(PROXY, False)
    
        EXECUTOR.submit(PROXY.start)
        while PROXY.status_bootstrap < 100 and not PROXY.exception:
            print(PROXY.status_bootstrap)
        set_system_proxy(PROXY, enabled=True)
        

if __name__ == "__main__":
    try:
        start_cli()
        # term background process fallback
        PROXY.process.terminate()
    except:
        raise
    finally:
        # revert proxy settings fallback
        set_system_proxy(PROXY, True)