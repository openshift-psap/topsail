import yaml
import logging
import sys

import pydantic

import wdm.model as model

def populate_predefined_tasks(filepath, predefined_tasks):
    with open(filepath) as f:
        docs = list(yaml.safe_load_all(f))

    class Model(pydantic.BaseModel):
        task: model.TaskModels

    for doc in docs:
        if doc is None: continue # empty block
        try:
            obj = Model.parse_obj(dict(task=doc))
            task = obj.task
        except pydantic.error_wrappers.ValidationError as e:
            logging.error(f"Failed to parse the YAML predefined file: {e}")
            logging.info("Faulty YAML entry:\n" + yaml.dump(doc))
            sys.exit(1)

        if task.name in predefined_tasks:
            logging.warning(f"Predefined task '{obj.name}' already known. Keeping only the first one.")
            continue

        predefined_tasks[task.name] = task

def populate_dependencies(filepath, dependencies, dependency_prefixes,
                          *, prefix, file_configuration=None):
    with open(filepath) as f:
        docs = list(yaml.safe_load_all(f))

    first_target = None
    for doc in docs:
        if doc is None: continue # empty block

        try: obj = model.DependencyModel.parse_obj(doc)
        except pydantic.error_wrappers.ValidationError as e:
            logging.error(f"Failed to parse the YAML dependency file '{filepath}': {e}")
            logging.info("Faulty YAML entry:\n" + yaml.dump(doc))
            sys.exit(1)

        if not obj.spec:
            if file_configuration:
                logging.error("File configuration already populated ...")
                sys.exit(1)
            if obj.config_values and file_configuration is None:
                logging.error("Library file '%s' cannot have a file 'configuration-values' field.", filepath)
                sys.exit(1)

            file_configuration.update(obj.config_values)
            continue

        obj.name = f"{prefix}{obj.name}"
        dependencies[obj.name] = obj
        dependency_prefixes[obj.name] = prefix

        if not first_target:
            first_target = obj.name

    return first_target
