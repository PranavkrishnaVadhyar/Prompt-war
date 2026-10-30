"""Explicit worker entry point. Never started by importing or setting up the project."""
from concurrent.futures import ThreadPoolExecutor
import time
from app.config import settings
from app import panel_jobs


def main():
    workers=settings().evaluation_workers
    print(f"Prompt War evaluation worker ready: {workers} submissions at once, four models per submission.")
    print("Only jobs explicitly requested by an organiser or judge will call providers.")
    with ThreadPoolExecutor(max_workers=workers,thread_name_prefix="prompt-war-submission") as pool:
        active=set()
        try:
            while True:
                finished={future for future in active if future.done()}
                for future in finished:
                    try:
                        future.result()
                    except Exception as error:
                        print("Evaluation job interrupted:",type(error).__name__,"— its lease will expire; retry from the panel.")
                active-=finished
                try:
                    panel_jobs.expire_abandoned()
                    while len(active)<workers:
                        job=panel_jobs.claim()
                        if not job:
                            break
                        active.add(pool.submit(panel_jobs.process,job))
                except Exception as error:
                    # No exception values, request bodies, tokens or credentials enter the log.
                    print("Evaluation queue unavailable:",type(error).__name__)
                time.sleep(2)
        except KeyboardInterrupt:
            print("Stopping; waiting for in-flight provider requests to finish.")


if __name__=="__main__":
    main()

