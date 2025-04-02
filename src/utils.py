import csv


def save_params_to_csv(
    module, print_values=True, shared_lib_path=None, filename="parameters.csv"
):
    """
    This function saves parameter information to a CSV file.

    Parameters:
        module: The module to retrieve parameter information from
        filename: Name of the output CSV file (default: 'parameters.csv')
        print_values: If True, saves the current parameter values as well
        shared_lib_path: Path of the shared library from which the module was loaded
    """

    # Gather output data in table
    output = []
    if print_values:
        headers = ["Parameter", "Type", "Default", "Current", "Steering", "Description"]
    else:
        headers = ["Parameter", "Type", "Default", "Description"]

    output.append(headers)

    has_forced_params = False
    paramList = module.available_params()

    for paramItem in paramList:
        defaultStr = str(paramItem.default)
        valueStr = str(paramItem.values)
        forceString = ""
        if paramItem.forceInSteering:
            forceString = "*"
            has_forced_params = True
            defaultStr = ""  # Required parameters don’t have default values

        if print_values:
            row = [
                forceString + paramItem.name,
                paramItem.type,
                defaultStr,
                valueStr,
                paramItem.setInSteering,
                paramItem.description,
            ]
        else:
            row = [
                forceString + paramItem.name,
                paramItem.type,
                defaultStr,
                paramItem.description,
            ]

        output.append(row)

    # Save to CSV file
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(output)

    print(f"[ADAK] {module.name()} parameters saved to {filename}...")
