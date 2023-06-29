from . import models
import matrix_benchmarking.store as store

store.register_lts_schema(models.QDupPayload)
