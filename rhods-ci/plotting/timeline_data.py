import datetime
import re

from .. import store as rhodsci_store

def get_text(what, start_evt, finish_evt, start, finish):
    duration_s = (finish - start).total_seconds()

    if duration_s < 120:
        duration = f"{duration_s:.1f} seconds"
    else:
        duration_min = duration_s / 60
        duration = f"{duration_min:.1f} minutes"

    if finish_evt:
        return f"{what}<br>FROM: {start_evt} ({start})<br>TO: {finish_evt} ({finish})<br>{duration}"
    else:
        return f"{what}<br>{start_evt}<br>{duration}"


def generate(entry, cfg):
    user_count = cfg.get("timeline.users", 20)

    entry_results = rhodsci_store._generate_timeline_results(entry, user_count) \
        if entry.settings.expe == "theoretical" \
           else entry.results

    user_count = len(entry_results.test_pods) or len(entry_results.notebook_pods)
    test_nodes = {}
    rhods_nodes = {}

    test_nodes_index = list(entry_results.testpod_hostnames.values()).index
    rhods_nodes_index = list(entry_results.notebook_hostnames.values()).index

    for testpod_name, nodename in entry_results.testpod_hostnames.items():
        user_idx = int(testpod_name.split("-")[2])
        test_nodes[user_idx] = f"Test node #{test_nodes_index(nodename)}"

    for notebook_name, nodename in entry_results.notebook_hostnames.items():
        user_idx = int(re.findall(r'[:letter:]*(\d+)$', notebook_name)[0])
        rhods_nodes[user_idx] = f"RHODS node #{rhods_nodes_index(nodename)}"

    def get_line_name(user_idx):
        line_name = [
            f"User #{user_idx:03d}",
        ]

        return "<br>".join(line_name)

    data = []

    for testpod_name in entry_results.test_pods:
        user_idx = int(testpod_name.split("-")[2])

        pod_times = entry_results.pod_times[testpod_name]

        event_times = entry_results.event_times[testpod_name]

        if not pod_times.__dict__: continue
        #if not event_times.__dict__.get("warnings", []): continue
        def generate_data(LegendName, start_evt, finish_evt, **kwargs):
            defaults = dict(
                LegendName=LegendName,
                LegendGroup="Test Pod",
                Start=kwargs.get("Start") or data[-1]["Finish"],
                Finish=kwargs["Finish"],
                LineName=get_line_name(user_idx),
                UserIdx=user_idx,
                Opacity=0.5,
                LineWidth=80,
                LineSortIndex=user_idx,
            )

            defaults["Text"] = get_text(LegendName,
                                        start_evt, finish_evt,
                                        defaults["Start"], defaults["Finish"])

            return defaults | kwargs

        data.append(generate_data(
            "01. Test pod scheduling",
            "Job creation", "Pod scheduled",
            Finish=event_times.scheduled,
            Start=entry_results.job_creation_time,))
        data.append(generate_data(
            "02. Test pod preparation",
            "Pod scheduled", "pulling image",
            Finish=event_times.pulling))
        data.append(generate_data(
            "03. Test pod image pull",
            "Pod pulling image", "image pulled",
            Finish=event_times.pulled))
        data.append(generate_data(
            "04. Test pod initialization",
            "Pod image pulled", "container started",
            Finish=pod_times.container_started))
        data.append(generate_data(
            "05. Test Execution",
            "Container started", "container finished",
            Finish=pod_times.container_finished))

        for reason, start, end, msg in event_times.__dict__.get("warnings", []):
            data.append(generate_data(
                "Test-pod K8s Warnings",
                reason, msg,
                Start=start,
                Finish=end,
                LineColor="Red",
                LineWidth=20,
                Opacity=0.9,
            ))

    data_length_before_ods_ci = len(data)

    for testpod_name, ods_ci_output in entry_results.ods_ci_output.items():
        user_idx = int(testpod_name.split("-")[2])

        for step_idx, (step_name, step_times) in enumerate(ods_ci_output.items()):
            def generate_data(LegendName, status, **kwargs):
                defaults = dict(
                    LegendName=LegendName,
                    LegendGroup="ODS-CI",
                    Start=kwargs.get("Start") or data[-1]["Finish"],
                    Finish=kwargs["Finish"],
                    LineName=get_line_name(user_idx),
                    UserIdx=user_idx,
                    Opacity=0.9,
                    LineWidth=50,
                    LineSortIndex=kwargs["Finish"],
                    Status=status,
                )

                defaults["Text"] = get_text(LegendName,
                                            f"Test result: {status}<br>FROM: {defaults['Start']}<br>TO: {defaults['Finish']}", None,
                                            defaults["Start"], defaults["Finish"])

                return defaults | kwargs

            data.append(generate_data(
                f"ODS - {step_idx} - {step_name}",
                step_times.status,
                Start=step_times.start,
                Finish=step_times.finish,
                StepIdx=step_idx
            ))

    for notebook_name in entry_results.notebook_pods:
        user_idx = int(re.findall(r'[:letter:]*(\d+)$', notebook_name)[0])

        event_times = entry_results.event_times[notebook_name]
        try: appears_time = min([v for v in event_times.__dict__.values() if isinstance(v, datetime.datetime)])
        except ValueError: #min() arg is an empty sequence
            appears_time = None

        def generate_data(LegendName, start_evt, finish_evt, **kwargs):
            defaults = dict(
                Start=kwargs.get("Start") or data[-1]["Finish"],
                Finish=kwargs["Finish"],
                LegendName=LegendName,
                LegendGroup="Notebook",
                Opacity=1,
                LineName=get_line_name(user_idx),
                UserIdx=user_idx,
                LineWidth=30,
                LineSortIndex=kwargs["Finish"],
            )

            defaults["Text"] = get_text(LegendName,
                                        start_evt, finish_evt,
                                        defaults["Start"], defaults["Finish"])

            return defaults | kwargs

        for _ in [True]: # for the 'continue keyword'
            if not appears_time: continue
            if not hasattr(event_times, "scheduled"): continue
            data.append(generate_data(
                "20. Notebook scheduling",
                "Notebook pod appeared", "scheduled",
                Start=appears_time,
                Finish=event_times.scheduled))
            if not hasattr(event_times, "pulling"): continue
            data.append(generate_data(
                "21. Notebook preparation",
                "Notebook pod cheduled", "image pulling",
                Finish=event_times.pulling))
            if not hasattr(event_times, "pulled"): continue
            data.append(generate_data(
                "22. Notebook image pull",
                "Notebook image pulling", "image pulled",
                Finish=event_times.pulled))
            if not hasattr(event_times, "started"): continue
            data.append(generate_data(
                "23. Notebook initialization",
                "Notebook image pulled", "container started",
                Finish=event_times.started))


            end = event_times.terminated if hasattr(event_times, "terminaned") \
                else entry_results.job_completion_time

            data.append(generate_data(
                "24. Notebook execution",
                "Notebook container started", "container terminated",
                Finish=end))


        for reason, start, end, msg in event_times.__dict__.get("warnings", []):
            data.append(generate_data(
                "Notebook K8s Warnings",
                reason, msg,
                Start=start,
                Finish=end,
                LineColor="Red",
                LineWidth=20,
                Opacity=0.9,
            ))

    for notebook_name in entry_results.notebook_hostnames.keys():
        user_idx = int(re.findall(r'[:letter:]*(\d+)$', notebook_name)[0])
        rhods_node = rhods_nodes[user_idx]

        LineName = get_line_name(user_idx)

        data.insert(0, dict(
            LegendName=rhods_node,
            Start=entry_results.job_creation_time - datetime.timedelta(minutes=1),
            Finish=entry_results.job_completion_time + datetime.timedelta(minutes=1),
            LineName=LineName,
            LineWidth=25,
            Opacity=0.2,
            Text=rhods_node,
            LegendGroup="Nodes",
            SkipFromMinMaxDate=True,
        ))

    LINE_SORT_LEGENT_NAME = "05. Test Execution"

    return user_count, data, LINE_SORT_LEGENT_NAME
