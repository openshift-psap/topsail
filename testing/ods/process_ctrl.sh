process_ctrl__wait_list=()

process_ctrl::run_in_bg() {
    "$@" &
    echo "Adding '$!' to the wait-list '${process_ctrl__wait_list[@]}' ..."
    process_ctrl__wait_list+=("$!")
}

process_ctrl::wait_bg_processes() {
    echo "Waiting for the background processes '${process_ctrl__wait_list[@]}' to terminate ..."
    for pid in ${process_ctrl__wait_list[@]}; do
        wait $pid # this syntax honors the `set -e` flag
    done
    echo "All the processes are done!"
    process_ctrl__wait_list=()
}

process_ctrl::kill_bg_processes() {
    echo "Killing the background processes '${process_ctrl__wait_list[@]}' still running ..."
    for pid in ${process_ctrl__wait_list[@]}; do
        kill -9 $pid 2>/dev/null || true
    done
    echo "All the processes have been terminated."
    process_ctrl__wait_list=()
}

process_ctrl::retry() {
    total_retries=$1
    shift
    retry_delay=$1
    shift

    tries=0
    retries_left=$total_retries
    while [[ $retries_left != 0 ]]; do
        tries=$(($tries + 1))
        if "$@";
        then
            echo "$@" "succeeded at the $tries/$total_retries try."
            return
        fi
        echo "Try $(($total_retries - $retries_left + 1))/$total_retries failed. " "$@"
        retries_left=$(($retries_left - 1))
        sleep $retry_delay
    done
    echo "$@" "failed after $tries tries..."
    false
}
