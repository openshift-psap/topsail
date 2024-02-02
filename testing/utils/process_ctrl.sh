unset process_ctrl__wait_list
declare -A process_ctrl__wait_list

process_ctrl::run_in_bg() {
    "$@" &
    pid=$!
    echo "Adding '$*' to the wait-list ... (pid=$pid)"
    process_ctrl__wait_list[$pid]="$*"
}

process_ctrl::wait_bg_processes() {
    echo "Waiting for the background processes '${!process_ctrl__wait_list[@]}' to terminate ..."
    while [[ "${!process_ctrl__wait_list[*]}" ]]; do
        wait -ppid -n ${!process_ctrl__wait_list[@]} && retcode=0 || retcode=$?
        command="${process_ctrl__wait_list[$pid]}"
        unset process_ctrl__wait_list[$pid]
        if [[ "$retcode" != "0" ]];
        then
            echo "Background process '$command' failed :( retcode=$retcode pid=$pid"
            return $retcode
        else
            echo "Background process '$command' finished successfully :)"
        fi
    done
    echo "All the processes are done!"
}

process_ctrl::kill_bg_processes() {
    echo "Killing the background processes still running ..."
    for pid in ${!process_ctrl__wait_list[@]}; do
        echo "- ${process_ctrl__wait_list[$pid]} (pid=$pid)"
        kill -KILL $pid 2>/dev/null || true
        unset process_ctrl__wait_list[$pid]
    done
    echo "All the processes have been terminated."
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

process_ctrl::run_finalizers() {
    [ ${#process_ctrl__finalizers[@]} -eq 0 ] && return
    set +x

    echo "Running exit finalizers: "
    for finalizer in "${process_ctrl__finalizers[@]}"
    do
        echo "-> $finalizer"
    done
    echo "---"
    for finalizer in "${process_ctrl__finalizers[@]}"
    do
        echo "Running finalizer '$finalizer' ..."
        $finalizer
    done
    echo "Run finalizers: all done."
}

if [[ ! -v process_ctrl::finalizers ]]; then
    echo "Initializing 'process_ctrl__finalizers' ..."
    process_ctrl__finalizers=()
    trap process_ctrl::run_finalizers EXIT
fi
