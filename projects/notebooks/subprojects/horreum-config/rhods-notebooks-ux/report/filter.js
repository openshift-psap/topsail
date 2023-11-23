({version, user_count, sleep_factor}) => {
    const versions = ["1.25.0", "1.26.0"];
    const desired_users = 5;
    const desired_sleep_factor = 3;

    return desired_sleep_factor === sleep_factor && desired_users === user_count && versions.indexOf(version) !== -1;
}
