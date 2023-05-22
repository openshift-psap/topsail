({version, user_count, sleep_factor, user_results}) => {
    let data = [];
    const END_STEP = "Go to JupyterLab Page";
    const PASS_STR = "PASS";

    let fails = 0;

    user_results.forEach((user) => {
        if(!user['succeeded']) {
            fails++;
        }
        let total_time = 0;
        user['steps'].forEach((step) => {
            total_time += step['duration'];
            if(step['name'] === END_STEP && step['status'] == PASS_STR) {
                data.push(total_time);
            }
        });
    });

    const quantiles = [1, .9, .75, .5, .25];
    let out_q = {};
    data.sort((a, b) => a - b);
    let len = data.length;
    quantiles.forEach((q) => {
        const pos = (len - 1) * q;
        const base = Math.floor(pos);
        const rest = pos - base;
        let val = data[base];
        if (data[base + 1] !== undefined) {
             val = data[base] + rest * (data[base + 1] - data[base]);
        }

        out_q[`${Math.floor(q * 100)}%`] = val;
    });

    return {
        'version': version,
        'user_count': user_count,
        'failures': fails,
        'sleep_factor': sleep_factor,
        'exec_time': out_q
    };
}
