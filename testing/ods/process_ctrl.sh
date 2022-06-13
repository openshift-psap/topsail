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
    echo "Killing the background processes '${wait_list[@]}' still running ..."
    for pid in ${process_ctrl__wait_list[@]}; do
        kill -9 $pid 2>/dev/null || true
    done
    echo "All the processes have been terminated."
    process_ctrl__wait_list=()
}
