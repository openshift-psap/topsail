import matrix_benchmarking.common as common
import logging

def run():
    logging.info("Hello world :)")

    for entry in common.Matrix.all_records():
        lts_payload = entry.results
        if not hasattr(lts_payload, "kpis"):
            logging.warning("Not KPIs available ...")
            continue

        kpis = lts_payload.kpis

        print(kpis.tostr())
        print()
        print("---")
        print()
        pass

    number_of_failures = 0

    return number_of_failures
