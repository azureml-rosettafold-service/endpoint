import os
from os.path import dirname, abspath
import shutil
import subprocess
from azureml.core import Run


def init():
    global datasets
    global src_path
    datasets = {}

    os.makedirs("outputs", exist_ok=True)

    run = Run.get_context()
    ws = run.experiment.workspace

    datasets_list = [
        "rosettafold_weights",
        "rosettafold_bfd",
        "rosettafold_UniRef",
        "rosettafold_pdb",
    ]
    for name in datasets_list:
        datasets[name] = ws.datasets[name]
        print(datasets[name])
        print(type(datasets[name]))
        print(f"Added dataset {datasets[name].name}")

    src_path = os.path.join(abspath(dirname(__file__)), "RoseTTAFold_Remote")

    cmd = (
        "git clone --branch amah/params"
        f" https://github.com/AliMahmoudzadeh/RoseTTAFold.git {src_path}"
    )
    subprocess.call(
        cmd,
        shell=True,
    )

    os.chdir(f'{src_path}')
    print(f"showing the contents of the working folder :{src_path}")
    print(os.listdir(src_path))

    print("Setting permission to the sh file")
    cmd = "chmod +x run_e2e_ver_param.sh"
    subprocess.call(
        cmd,
        shell=True,
    )
    cmd = "chmod +x input_prep/make_msa.sh"
    subprocess.call(
        cmd,
        shell=True,
    )
    cmd = "chmod +x input_prep/make_ss.sh"
    subprocess.call(
        cmd,
        shell=True,
    )
    print("Batch init complete!")


def run(mini_batch):
    print(f"run method start: {__file__}, run({mini_batch})")
    result_list = []

    local_output = os.path.join(
        abspath(dirname(__file__)),
        "outputs",
    )
    os.makedirs(local_output, exist_ok=True)

    print("Starting to mount")
    mount_contexts = {}
    for name, dataset in datasets.items():
        mount_contexts[name] = dataset.mount()
        mount_contexts[name].start()
    print("Mount compelte")

    for input_file in mini_batch:

        input_dir = os.path.dirname(input_file)
        input_filename = os.path.basename(input_file).split(".")[0]
        print(f"Processing input {input_filename} in directory {input_dir}")

        # creating a working dir for this input
        temp_wd = os.path.join(abspath(dirname(__file__)), "outputs/{}".format(input_filename))
        os.makedirs(temp_wd, exist_ok=True)
        print(f"Temp wd {temp_wd}")

        os.chdir(f'{src_path}')


        cmd = [
            '/bin/sh',
            "./run_e2e_ver_param.sh",
            input_file,
            temp_wd,
            mount_contexts["rosettafold_pdb"].mount_point,
            mount_contexts["rosettafold_UniRef"].mount_point,
            mount_contexts["rosettafold_bfd"].mount_point,
            abspath("/RoseTTAFold/csblast-2.2.3"),
            mount_contexts["rosettafold_weights"].mount_point,
        ]
        print(f"Running command: {' '.join(cmd)}")
        p = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        _ = p.communicate()

        result_list.append("{}: {}".format(os.path.basename(input_file), input_file))


        # write outputs
        output_root = os.environ["AZUREML_BI_OUTPUT_PATH"]
        output_dir = os.path.join(output_root, input_filename)
        os.makedirs(output_dir, exist_ok=True)
        print(f"Moving outputs to {output_dir}")
        OUTPUT_FILENAME = "t000.e2e.pdb"  # filename is hard-coded in Rosetta Fold code
        if OUTPUT_FILENAME in os.listdir(temp_wd):
            shutil.copy(
                os.path.join(temp_wd, OUTPUT_FILENAME),
                output_dir,
                )
            print(f"Output written for input file {input_filename}")
    
    # post mini batch
    for name, mount_context in mount_contexts.items():
        mount_context.stop()

    return result_list
