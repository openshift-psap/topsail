import logging
import pathlib

from common import env, config, run
import prepare_odh, prepare_common, prepare_gpu

        
def prepare():
    """
    Prepares the cluster and the namespace for running the Codeflare-SDK user test
    """

    
    prepare_common.prepare_common()

        
    
def cleanup_cluster():
    """
    Restores the cluster to its original state
    """
    prepare_common.cleanup_cluster_common()
    
