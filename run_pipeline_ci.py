import logging
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def run_step(step_name, script_name):
    logging.info(f"STARTING: {step_name} ({script_name})")
    result = subprocess.run([sys.executable, script_name], capture_output=True, text=True)
    if result.stdout:
        print(result.stdout.strip())
    if result.returncode != 0:
        logging.error(f"FAILED: {step_name} | Error:\n{result.stderr.strip()}")
        sys.exit(1)
    logging.info(f"PASSED: {step_name}")


if __name__ == "__main__":
    logging.info("=== MTS DATA WAREHOUSE CI/CD PIPELINE STARTED ===")
    # Quality Gate 1: Run automated unit tests first; abort ETL if tests fail!
    run_step("Automated Unit Tests", "test_de_pipeline.py")
    # Quality Gate 2: Run incremental Star Schema ETL & Excel Serving Layer
    run_step("Incremental Star Schema ETL", "de_etl_lab.py")
    logging.info("=== PIPELINE COMPLETED SUCCESSFULLY ===")
