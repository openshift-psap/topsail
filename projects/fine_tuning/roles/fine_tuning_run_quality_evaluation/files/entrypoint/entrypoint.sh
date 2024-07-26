# !/bin/bash

set -o pipefail
set -o errexit
set -o nounset
set -o errtrace
set -x

echo "Transformer version"
#pip freeze | grep transformers

if [[ "${CONFIG_JSON_PATH:-}" ]]; then
    echo "Configuration:"
    cat "${CONFIG_JSON_PATH}"
else
    echo "No config file ..."
fi

echo Simulating the quality evaluation ...
sleep 1

set +x
echo "Simulation done. Showing the JSON results."
echo "=== JSON output follows ==="
cat <<EOF
[
	{
		"color": "red",
		"value": "#f00"
	},
	{
		"color": "green",
		"value": "#0f0"
	},
	{
		"color": "blue",
		"value": "#00f"
	},
	{
		"color": "cyan",
		"value": "#0ff"
	},
	{
		"color": "magenta",
		"value": "#f0f"
	},
	{
		"color": "yellow",
		"value": "#ff0"
	},
	{
		"color": "black",
		"value": "#000"
	}
]
EOF
