"""
Monitor job progress and send hints.
"""
import asyncio

from xsarena.core.jobs.model import JobManager


async def main():
    job_id = input("Enter job ID: ")

    job_mgr = JobManager()
    job = job_mgr.load(job_id)

    print(f"Job: {job.name}")
    print(f"State: {job.state}")
    print(f"Progress: {job.chunks_done}/{job.max_chunks}")

    # Send hint for next chunk
    if job.state == "RUNNING":
        hint = input("Enter hint for next chunk (or press Enter to skip): ")
        if hint:
            await job_mgr.send_control_message(job_id, "next", hint)
            print("Hint sent!")


if __name__ == "__main__":
    asyncio.run(main())
