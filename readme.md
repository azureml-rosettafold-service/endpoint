# RosettaFold Batch Endpoint on Azure ML

## Introduction

Azure is collaborating with the Baker Lab to expose their Rosetta Fold model as a service. This document describes how to get started exploring Rosetta Fold on Azure Machine Learning (Azure ML) by exposing the model as a batch endpoint. This endpoint provides a way to securely run parallel inferencing jobs against Rosetta Fold via the CLI.

**Note.** This Rosetta Fold endpoint is not designed to run in production environments, and is strictly for non-production test environments.


## Setup

This repo contains the following key files:

- `create-endpoint.yml`: Configuration file to create the Azure ML batch inferencing endpoint
- `score.py`: Script running the inferencing code behind the endpoint.
- `dockerfile`: Configuration file for the environment than runs on the AmlCompute (VM).

To setup the RosettaFold endpoint run the following:

1. Install the Azure ML CLI ([instructions](https://docs.microsoft.com/en-us/azure/machine-learning/how-to-configure-cli))
  - Test installation with `az --version`
2. The endpoint assumes there is a compute target called `gpu-cluster` assocaited to your Azure ML workspace. This can be created with the CLI:

```bash
az ml compute create --name gpu-cluster --type AMLCompute --size Standard_NC12 --min-instances 0 --max-instances 10
```

3. The endpoint assumes the databases required for RoseTTAFold are available via registered datasets in the workspace.
   The data is available in a [public blob storage](https://ms.portal.azure.com/#blade/Microsoft_Azure_Storage/ContainerMenuBlade/overview/storageAccountId/%2Fsubscriptions%2F48bbc269-ce89-4f6f-9a12-c6f91fcb772d%2FresourceGroups%2Faml1p-rg%2Fproviders%2FMicrosoft.Storage%2FstorageAccounts%2Frosettafold/path/rosettafold-dependencies%2Fdbs%2FUniRef%2F), under these paths:
   - rosettafold_weights :"weights/"
   - rosettafold_bfd :"dbs/bfd/bfd/"
   - rosettafold_UniRef:"dbs/UniRef/"
   - rosettafold_pdb:"dbs/pdb/"
    
4. Create the endpoint

```
az ml endpoint create --type batch --file create-batch-endpoint.yml
```

## Usage

The endpoint is designed to process input files containing protein sequences of the form:

```
>T1078 Tsp1, Trichoderma virens, 138 residues|
MAAPTPADKSMMAAVPEWTITNLKRVCNAGNTSCTWTFGVDTHLATATSCTYVVKANANASQASGGPVTCGPYTITSSWSGQFGPNNGFTTFAVTDFSKKLIVWPAYTDVQVQAGKVVSPNQSYAPANLPLEHHHHHH
```

**Note.** Each input should be provided in its own input file. The input file name will be used to identify the corresponding output, so use unique input names.


### Call endpoint with single local file

```
az ml endpoint invoke --name rosettafold --type batch –input-local-path <local/path/to>/input.fa
```

### Call endpoint with single remote file

Given a single input file stored in Azure Blob Storage, grab the corresponding URL: `https://<storage-account-name>.blob.core.windows.net/<storage-container>/<path/on/container>/input.fa`, invoke the endpoint with:

```
az ml endpoint invoke --name rosettafold --type batch --input-path https://<storage-account-name>.blob.core.windows.net/<storage-container>/<path/on/container>/input.fa
```

### Call the endpoint with multiple files

Run this exactly as above, only now pointing to a directory containing multiple files e.g.

```
az ml endpoint invoke --name rosettafold --type batch --input-path https://<storage-account-name>.blob.core.windows.net/<storage-container>/<path/on/container>/
```

### Reading output

When the inferencing job is complete, output files will be uploaded to the workspace default Azure Blob Storage account with the following location:

```
https://<default-storage-account>.blob.core.windows.net/<default-container>/azureml/<run-id>/score/<input-filename>/t000.e2e.pdb
```

## Configuring Parallelism

When setting up the endpoint we configured the instance count, and the minibatch size parameters. These control the how the inference jobs will scale up.

- Instance count: the maximum number of nodes (VMs) that will spin up.
- Minibatch size: the maximum number of examples that will be processed at a time per-node.
A minibatch is sent to each instance, where it will be processed sequentially. Once that node completes its minibatch it will be sent another (assuming there are any remaining inputs to be processed).

## REST Endpoint

Batch endpoints can also be invoked via a REST endpoint as follows. Here is an example.

1.	Get batch endpoint scoring uri:
```
scoring_uri=$(az ml endpoint show --name rosettafold --type batch --query scoring_uri -o tsv)
```

2.	Get authentication token:
```
auth_token=$(az account get-access-token --query accessToken -o tsv)
```

3.	Kick off inferencing job via CURL:

```
curl --location --request POST "$scoring_uri" --header "Authorization: Bearer $auth_token" --header "Content-Type: application/json" --data-raw "{'properties': {'dataset': {'dataInputType': 'DataUrl', 'Path': 'https://amsaiedws3295876841.blob.core.windows.net/azureml-blobstore-febe82a7-da37-4f81-85d5-48c8a0082e47/rosetta/input_samples/inputs.fa'}}}"
```


## Example

We provide concrete example of an input/output pair.

### Example Input

```
>T1078 Tsp1, Trichoderma virens, 138 residues|
MAAPTPADKSMMAAVPEWTITNLKRVCNAGNTSCTWTFGVDTHLATATSCTYVVKANANASQASGGPVTCGPYTITSSWSGQFGPNNGFTTFAVTDFSKKLIVWPAYTDVQVQAGKVVSPNQSYAPANLPLEHHHHHH
```

### Example Output

```
ATOM      1  N   MET A   1      -0.043  37.353 -17.564  1.00  0.36
ATOM      2  CA  MET A   1      -0.274  36.236 -16.653  1.00  0.36
ATOM      3  C   MET A   1       0.677  35.098 -16.940  1.00  0.36
ATOM      4  O   MET A   1       1.719  35.291 -17.566  1.00  0.36
ATOM      5  N   ALA A   2       0.278  33.883 -16.455  1.00  0.34
ATOM      6  CA  ALA A   2       1.184  32.794 -16.808  1.00  0.34
ATOM      7  C   ALA A   2       1.177  31.720 -15.746  1.00  0.34
ATOM      8  O   ALA A   2       0.241  31.627 -14.951  1.00  0.34
ATOM      9  N   ALA A   3       2.226  30.914 -15.740  1.00  0.33
ATOM     10  CA  ALA A   3       2.445  29.833 -14.783  1.00  0.33
ATOM     11  C   ALA A   3       3.875  29.349 -14.833  1.00  0.33
ATOM     12  O   ALA A   3       4.432  28.926 -13.819  1.00  0.33
ATOM     13  N   PRO A   4       4.453  29.409 -15.980  1.00  0.35
ATOM     14  CA  PRO A   4       5.810  28.910 -16.185  1.00  0.35
ATOM     15  C   PRO A   4       5.796  27.608 -16.950  1.00  0.35
ATOM     16  O   PRO A   4       4.835  27.301 -17.655  1.00  0.35
ATOM     17  N   THR A   5       6.798  26.797 -16.872  1.00  0.32
ATOM     18  CA  THR A   5       6.728  25.429 -17.379  1.00  0.32
ATOM     19  C   THR A   5       8.105  24.816 -17.471  1.00  0.32
ATOM     20  O   THR A   5       8.311  23.668 -17.079  1.00  0.32
ATOM     21  N   PRO A   6       9.133  25.478 -17.970  1.00  0.38
ATOM     22  CA  PRO A   6      10.468  24.954 -17.698  1.00  0.38
ATOM     23  C   PRO A   6      11.508  25.664 -18.532  1.00  0.38
ATOM     24  O   PRO A   6      12.546  26.085 -18.021  1.00  0.38
ATOM     25  N   ALA A   7      11.127  25.713 -19.660  1.00  0.38
ATOM     26  CA  ALA A   7      12.025  25.458 -20.783  1.00  0.38
ATOM     27  C   ALA A   7      13.149  24.534 -20.377  1.00  0.38
ATOM     28  O   ALA A   7      12.911  23.427 -19.896  1.00  0.38
ATOM     29  N   ASP A   8      14.376  24.963 -20.560  1.00  0.39
ATOM     30  CA  ASP A   8      15.564  24.304 -20.023  1.00  0.39
ATOM     31  C   ASP A   8      16.550  25.317 -19.492  1.00  0.39
ATOM     32  O   ASP A   8      16.262  26.035 -18.534  1.00  0.39
ATOM     33  N   LYS A   9      17.708  25.500 -19.974  1.00  0.40
ATOM     34  CA  LYS A   9      18.615  26.483 -19.388  1.00  0.40
ATOM     35  C   LYS A   9      19.519  25.841 -18.363  1.00  0.40
ATOM     36  O   LYS A   9      19.733  24.629 -18.383  1.00  0.40
ATOM     37  N   SER A  10      20.049  26.680 -17.458  1.00  0.43
ATOM     38  CA  SER A  10      20.860  26.064 -16.412  1.00  0.43
ATOM     39  C   SER A  10      21.321  27.094 -15.409  1.00  0.43
ATOM     40  O   SER A  10      20.730  28.167 -15.290  1.00  0.43
ATOM     41  N   MET A  11      22.324  26.717 -14.762  1.00  0.47
ATOM     42  CA  MET A  11      22.361  26.702 -13.303  1.00  0.47
ATOM     43  C   MET A  11      21.302  25.782 -12.745  1.00  0.47
ATOM     44  O   MET A  11      21.270  25.512 -11.544  1.00  0.47
ATOM     45  N   MET A  12      20.540  25.388 -13.656  1.00  0.52
ATOM     46  CA  MET A  12      19.475  24.449 -13.319  1.00  0.52
ATOM     47  C   MET A  12      20.043  23.154 -12.790  1.00  0.52
ATOM     48  O   MET A  12      21.162  23.119 -12.279  1.00  0.52
ATOM     49  N   ALA A  13      19.278  22.159 -12.925  1.00  0.53
ATOM     50  CA  ALA A  13      19.616  20.936 -12.203  1.00  0.53
ATOM     51  C   ALA A  13      18.891  19.747 -12.786  1.00  0.53
ATOM     52  O   ALA A  13      17.855  19.896 -13.433  1.00  0.53
ATOM     53  N   ALA A  14      19.580  18.915 -12.431  1.00  0.59
ATOM     54  CA  ALA A  14      19.193  17.558 -12.808  1.00  0.59
ATOM     55  C   ALA A  14      18.416  16.890 -11.699  1.00  0.59
ATOM     56  O   ALA A  14      17.218  16.642 -11.830  1.00  0.59
ATOM     57  N   VAL A  15      19.081  16.635 -10.700  1.00  0.64
ATOM     58  CA  VAL A  15      18.259  16.182  -9.581  1.00  0.64
ATOM     59  C   VAL A  15      16.841  15.918 -10.026  1.00  0.64
ATOM     60  O   VAL A  15      16.599  15.092 -10.906  1.00  0.64
ATOM     61  N   PRO A  16      16.009  16.644  -9.380  1.00  0.69
ATOM     62  CA  PRO A  16      14.624  16.233  -9.591  1.00  0.69
ATOM     63  C   PRO A  16      13.756  17.417  -9.944  1.00  0.69
ATOM     64  O   PRO A  16      14.177  18.567  -9.814  1.00  0.69
ATOM     65  N   GLU A  17      12.817  17.070 -10.287  1.00  0.73
ATOM     66  CA  GLU A  17      11.747  17.968 -10.708  1.00  0.73
ATOM     67  C   GLU A  17      10.685  18.082  -9.640  1.00  0.73
ATOM     68  O   GLU A  17      10.444  17.138  -8.888  1.00  0.73
ATOM     69  N   TRP A  18      10.065  19.159  -9.548  1.00  0.76
ATOM     70  CA  TRP A  18       9.045  19.342  -8.520  1.00  0.76
ATOM     71  C   TRP A  18       7.699  19.630  -9.140  1.00  0.76
ATOM     72  O   TRP A  18       7.615  20.195 -10.230  1.00  0.76
ATOM     73  N   THR A  19       6.794  19.261  -8.474  1.00  0.79
ATOM     74  CA  THR A  19       5.437  19.499  -8.956  1.00  0.79
ATOM     75  C   THR A  19       4.566  20.065  -7.860  1.00  0.79
ATOM     76  O   THR A  19       4.520  19.530  -6.752  1.00  0.79
ATOM     77  N   ILE A  20       3.901  21.127  -8.201  1.00  0.79
ATOM     78  CA  ILE A  20       2.961  21.690  -7.236  1.00  0.79
ATOM     79  C   ILE A  20       1.553  21.222  -7.517  1.00  0.79
ATOM     80  O   ILE A  20       1.019  21.447  -8.602  1.00  0.79
ATOM     81  N   THR A  21       0.980  20.614  -6.617  1.00  0.83
ATOM     82  CA  THR A  21      -0.321  19.988  -6.836  1.00  0.83
ATOM     83  C   THR A  21      -1.327  20.460  -5.814  1.00  0.83
ATOM     84  O   THR A  21      -0.980  20.719  -4.661  1.00  0.83
ATOM     85  N   ASN A  22      -2.587  20.554  -6.311  1.00  0.82
ATOM     86  CA  ASN A  22      -3.693  20.805  -5.391  1.00  0.82
ATOM     87  C   ASN A  22      -3.643  22.218  -4.860  1.00  0.82
ATOM     88  O   ASN A  22      -3.867  22.453  -3.672  1.00  0.82
ATOM     89  N   LEU A  23      -3.372  23.075  -5.681  1.00  0.81
ATOM     90  CA  LEU A  23      -3.359  24.475  -5.265  1.00  0.81
ATOM     91  C   LEU A  23      -4.764  24.996  -5.077  1.00  0.81
ATOM     92  O   LEU A  23      -5.578  24.960  -6.000  1.00  0.81
ATOM     93  N   LYS A  24      -5.037  25.458  -3.939  1.00  0.86
ATOM     94  CA  LYS A  24      -6.373  25.952  -3.620  1.00  0.86
ATOM     95  C   LYS A  24      -6.301  27.153  -2.707  1.00  0.86
ATOM     96  O   LYS A  24      -5.380  27.275  -1.899  1.00  0.86
ATOM     97  N   ARG A  25      -7.166  27.956  -2.810  1.00  0.87
ATOM     98  CA  ARG A  25      -7.214  29.154  -1.978  1.00  0.87
ATOM     99  C   ARG A  25      -8.589  29.343  -1.383  1.00  0.87
ATOM    100  O   ARG A  25      -9.599  29.209  -2.074  1.00  0.87
ATOM    101  N   VAL A  26      -8.564  29.627  -0.209  1.00  0.86
ATOM    102  CA  VAL A  26      -9.835  29.845   0.475  1.00  0.86
ATOM    103  C   VAL A  26      -9.822  31.147   1.240  1.00  0.86
ATOM    104  O   VAL A  26      -8.912  31.406   2.027  1.00  0.86
ATOM    105  N   CYS A  27     -10.728  31.936   1.062  1.00  0.87
ATOM    106  CA  CYS A  27     -10.793  33.256   1.683  1.00  0.87
ATOM    107  C   CYS A  27     -11.975  33.357   2.617  1.00  0.87
ATOM    108  O   CYS A  27     -12.999  32.705   2.410  1.00  0.87
ATOM    109  N   ASN A  28     -11.748  34.123   3.519  1.00  0.86
ATOM    110  CA  ASN A  28     -12.866  34.406   4.415  1.00  0.86
ATOM    111  C   ASN A  28     -13.836  35.373   3.780  1.00  0.86
ATOM    112  O   ASN A  28     -13.504  36.052   2.809  1.00  0.86
ATOM    113  N   ALA A  29     -14.963  35.437   4.287  1.00  0.83
ATOM    114  CA  ALA A  29     -16.036  36.209   3.667  1.00  0.83
ATOM    115  C   ALA A  29     -15.608  37.638   3.432  1.00  0.83
ATOM    116  O   ALA A  29     -15.760  38.168   2.331  1.00  0.83
ATOM    117  N   GLY A  30     -15.154  38.197   4.276  1.00  0.81
ATOM    118  CA  GLY A  30     -14.799  39.600   4.084  1.00  0.81
ATOM    119  C   GLY A  30     -13.462  39.730   3.394  1.00  0.81
ATOM    120  O   GLY A  30     -13.058  40.826   3.006  1.00  0.81
ATOM    121  N   ASN A  31     -12.766  38.519   3.252  1.00  0.85
ATOM    122  CA  ASN A  31     -11.501  38.539   2.523  1.00  0.85
ATOM    123  C   ASN A  31     -10.412  39.180   3.350  1.00  0.85
ATOM    124  O   ASN A  31      -9.572  39.912   2.827  1.00  0.85
ATOM    125  N   THR A  32     -10.405  38.944   4.516  1.00  0.89
ATOM    126  CA  THR A  32      -9.381  39.458   5.421  1.00  0.89
ATOM    127  C   THR A  32      -8.249  38.469   5.572  1.00  0.89
ATOM    128  O   THR A  32      -7.092  38.857   5.735  1.00  0.89
ATOM    129  N   SER A  33      -8.598  37.190   5.514  1.00  0.89
ATOM    130  CA  SER A  33      -7.584  36.143   5.588  1.00  0.89
ATOM    131  C   SER A  33      -7.776  35.125   4.490  1.00  0.89
ATOM    132  O   SER A  33      -8.906  34.814   4.110  1.00  0.89
ATOM    133  N   CYS A  34      -6.735  34.668   4.044  1.00  0.87
ATOM    134  CA  CYS A  34      -6.792  33.654   2.995  1.00  0.87
ATOM    135  C   CYS A  34      -5.865  32.503   3.305  1.00  0.87
ATOM    136  O   CYS A  34      -4.781  32.698   3.854  1.00  0.87
ATOM    137  N   THR A  35      -6.268  31.396   2.976  1.00  0.88
ATOM    138  CA  THR A  35      -5.452  30.211   3.218  1.00  0.88
ATOM    139  C   THR A  35      -5.150  29.489   1.927  1.00  0.88
ATOM    140  O   THR A  35      -6.061  29.102   1.194  1.00  0.88
ATOM    141  N   TRP A  36      -3.904  29.314   1.656  1.00  0.87
ATOM    142  CA  TRP A  36      -3.498  28.607   0.445  1.00  0.87
ATOM    143  C   TRP A  36      -2.982  27.226   0.772  1.00  0.87
ATOM    144  O   TRP A  36      -2.131  27.062   1.646  1.00  0.87
ATOM    145  N   THR A  37      -3.483  26.290   0.096  1.00  0.88
ATOM    146  CA  THR A  37      -3.074  24.914   0.360  1.00  0.88
ATOM    147  C   THR A  37      -2.521  24.266  -0.887  1.00  0.88
ATOM    148  O   THR A  37      -3.135  24.324  -1.952  1.00  0.88
ATOM    149  N   PHE A  38      -1.388  23.683  -0.688  1.00  0.83
ATOM    150  CA  PHE A  38      -0.753  23.048  -1.839  1.00  0.83
ATOM    151  C   PHE A  38      -0.006  21.803  -1.425  1.00  0.83
ATOM    152  O   PHE A  38       0.262  21.593  -0.242  1.00  0.83
ATOM    153  N   GLY A  39       0.291  21.063  -2.344  1.00  0.84
ATOM    154  CA  GLY A  39       1.119  19.880  -2.126  1.00  0.84
ATOM    155  C   GLY A  39       2.367  19.930  -2.974  1.00  0.84
ATOM    156  O   GLY A  39       2.330  20.365  -4.124  1.00  0.84
ATOM    157  N   VAL A  40       3.409  19.531  -2.497  1.00  0.84
ATOM    158  CA  VAL A  40       4.670  19.539  -3.232  1.00  0.84
ATOM    159  C   VAL A  40       5.212  18.138  -3.391  1.00  0.84
ATOM    160  O   VAL A  40       5.367  17.408  -2.412  1.00  0.84
ATOM    161  N   ASP A  41       5.487  17.761  -4.514  1.00  0.84
ATOM    162  CA  ASP A  41       5.956  16.408  -4.800  1.00  0.84
ATOM    163  C   ASP A  41       7.277  16.437  -5.530  1.00  0.84
ATOM    164  O   ASP A  41       7.466  17.221  -6.461  1.00  0.84
ATOM    165  N   THR A  42       8.193  15.606  -5.137  1.00  0.75
ATOM    166  CA  THR A  42       9.521  15.602  -5.743  1.00  0.75
ATOM    167  C   THR A  42       9.818  14.267  -6.385  1.00  0.75
ATOM    168  O   THR A  42      10.933  13.756  -6.289  1.00  0.75
ATOM    169  N   HIS A  43       9.193  13.769  -6.876  1.00  0.72
ATOM    170  CA  HIS A  43       9.463  12.480  -7.505  1.00  0.72
ATOM    171  C   HIS A  43      10.458  11.682  -6.697  1.00  0.72
ATOM    172  O   HIS A  43      10.670  10.496  -6.950  1.00  0.72
ATOM    173  N   LEU A  44      11.159  12.247  -5.656  1.00  0.70
ATOM    174  CA  LEU A  44      12.121  11.537  -4.819  1.00  0.70
ATOM    175  C   LEU A  44      11.489  11.104  -3.518  1.00  0.70
ATOM    176  O   LEU A  44      11.953  10.163  -2.874  1.00  0.70
ATOM    177  N   ALA A  45      10.444  11.797  -3.158  1.00  0.77
ATOM    178  CA  ALA A  45       9.772  11.557  -1.884  1.00  0.77
ATOM    179  C   ALA A  45       8.272  11.551  -2.057  1.00  0.77
ATOM    180  O   ALA A  45       7.766  11.665  -3.173  1.00  0.77
ATOM    181  N   THR A  46       7.532  11.428  -1.044  1.00  0.86
ATOM    182  CA  THR A  46       6.074  11.499  -1.033  1.00  0.86
ATOM    183  C   THR A  46       5.602  12.931  -1.122  1.00  0.86
ATOM    184  O   THR A  46       6.377  13.864  -0.909  1.00  0.86
ATOM    185  N   ALA A  47       4.296  13.177  -1.444  1.00  0.89
ATOM    186  CA  ALA A  47       3.783  14.544  -1.472  1.00  0.89
ATOM    187  C   ALA A  47       3.740  15.133  -0.082  1.00  0.89
ATOM    188  O   ALA A  47       3.522  14.421   0.898  1.00  0.89
ATOM    189  N   THR A  48       3.939  16.356  -0.033  1.00  0.87
ATOM    190  CA  THR A  48       3.944  17.043   1.255  1.00  0.87
ATOM    191  C   THR A  48       2.949  18.178   1.267  1.00  0.87
ATOM    192  O   THR A  48       2.937  19.015   0.364  1.00  0.87
ATOM    193  N   SER A  49       2.150  18.227   2.224  1.00  0.92
ATOM    194  CA  SER A  49       1.143  19.280   2.318  1.00  0.92
ATOM    195  C   SER A  49       1.739  20.551   2.874  1.00  0.92
ATOM    196  O   SER A  49       2.525  20.516   3.821  1.00  0.92
ATOM    197  N   CYS A  50       1.334  21.605   2.255  1.00  0.90
ATOM    198  CA  CYS A  50       1.808  22.910   2.706  1.00  0.90
ATOM    199  C   CYS A  50       0.674  23.904   2.771  1.00  0.90
ATOM    200  O   CYS A  50      -0.177  23.948   1.883  1.00  0.90
ATOM    201  N   THR A  51       0.632  24.714   3.807  1.00  0.91
ATOM    202  CA  THR A  51      -0.442  25.687   3.978  1.00  0.91
ATOM    203  C   THR A  51       0.113  27.055   4.297  1.00  0.91
ATOM    204  O   THR A  51       0.923  27.208   5.211  1.00  0.91
ATOM    205  N   TYR A  52      -0.298  27.989   3.588  1.00  0.88
ATOM    206  CA  TYR A  52       0.132  29.363   3.830  1.00  0.88
ATOM    207  C   TYR A  52      -1.048  30.250   4.148  1.00  0.88
ATOM    208  O   TYR A  52      -2.073  30.204   3.468  1.00  0.88
ATOM    209  N   VAL A  53      -0.925  31.018   5.123  1.00  0.91
ATOM    210  CA  VAL A  53      -2.004  31.905   5.548  1.00  0.91
ATOM    211  C   VAL A  53      -1.599  33.353   5.409  1.00  0.91
ATOM    212  O   VAL A  53      -0.550  33.764   5.904  1.00  0.91
ATOM    213  N   VAL A  54      -2.450  34.063   4.743  1.00  0.90
ATOM    214  CA  VAL A  54      -2.176  35.488   4.580  1.00  0.90
ATOM    215  C   VAL A  54      -3.194  36.322   5.320  1.00  0.90
ATOM    216  O   VAL A  54      -4.397  36.078   5.225  1.00  0.90
ATOM    217  N   LYS A  55      -2.765  37.200   5.977  1.00  0.93
ATOM    218  CA  LYS A  55      -3.635  38.083   6.747  1.00  0.93
ATOM    219  C   LYS A  55      -3.420  39.527   6.359  1.00  0.93
ATOM    220  O   LYS A  55      -2.287  39.959   6.144  1.00  0.93
ATOM    221  N   ALA A  56      -4.440  40.223   6.277  1.00  0.88
ATOM    222  CA  ALA A  56      -4.354  41.621   5.866  1.00  0.88
ATOM    223  C   ALA A  56      -5.507  42.420   6.425  1.00  0.88
ATOM    224  O   ALA A  56      -6.470  41.857   6.945  1.00  0.88
ATOM    225  N   ASN A  57      -5.343  43.595   6.290  1.00  0.77
ATOM    226  CA  ASN A  57      -6.326  44.497   6.884  1.00  0.77
ATOM    227  C   ASN A  57      -7.453  44.779   5.919  1.00  0.77
ATOM    228  O   ASN A  57      -8.563  45.118   6.329  1.00  0.77
ATOM    229  N   ALA A  58      -7.242  44.665   4.778  1.00  0.76
ATOM    230  CA  ALA A  58      -8.310  45.026   3.849  1.00  0.76
ATOM    231  C   ALA A  58      -8.523  43.938   2.823  1.00  0.76
ATOM    232  O   ALA A  58      -9.659  43.569   2.523  1.00  0.76
ATOM    233  N   ASN A  59      -7.603  43.497   2.360  1.00  0.79
ATOM    234  CA  ASN A  59      -7.906  42.486   1.352  1.00  0.79
ATOM    235  C   ASN A  59      -6.764  41.509   1.205  1.00  0.79
ATOM    236  O   ASN A  59      -5.630  41.902   0.931  1.00  0.79
ATOM    237  N   ALA A  60      -6.999  40.469   1.352  1.00  0.80
ATOM    238  CA  ALA A  60      -6.021  39.394   1.489  1.00  0.80
ATOM    239  C   ALA A  60      -5.753  38.735   0.157  1.00  0.80
ATOM    240  O   ALA A  60      -4.613  38.397  -0.161  1.00  0.80
ATOM    241  N   SER A  61      -6.660  38.575  -0.526  1.00  0.78
ATOM    242  CA  SER A  61      -6.541  38.010  -1.867  1.00  0.78
ATOM    243  C   SER A  61      -5.534  38.779  -2.689  1.00  0.78
ATOM    244  O   SER A  61      -5.118  38.330  -3.757  1.00  0.78
ATOM    245  N   GLN A  62      -5.116  39.878  -2.286  1.00  0.80
ATOM    246  CA  GLN A  62      -4.189  40.715  -3.042  1.00  0.80
ATOM    247  C   GLN A  62      -2.885  40.885  -2.299  1.00  0.80
ATOM    248  O   GLN A  62      -1.967  41.547  -2.783  1.00  0.80
ATOM    249  N   ALA A  63      -2.881  40.294  -1.198  1.00  0.81
ATOM    250  CA  ALA A  63      -1.688  40.429  -0.367  1.00  0.81
ATOM    251  C   ALA A  63      -0.657  39.387  -0.730  1.00  0.81
ATOM    252  O   ALA A  63      -0.959  38.416  -1.422  1.00  0.81
ATOM    253  N   SER A  64       0.349  39.652  -0.281  1.00  0.81
ATOM    254  CA  SER A  64       1.450  38.714  -0.476  1.00  0.81
ATOM    255  C   SER A  64       1.625  37.827   0.733  1.00  0.81
ATOM    256  O   SER A  64       1.260  38.202   1.847  1.00  0.81
ATOM    257  N   GLY A  65       2.061  36.912   0.547  1.00  0.78
ATOM    258  CA  GLY A  65       2.263  35.954   1.631  1.00  0.78
ATOM    259  C   GLY A  65       3.730  35.642   1.810  1.00  0.78
ATOM    260  O   GLY A  65       4.500  36.480   2.279  1.00  0.78
ATOM    261  N   GLY A  66       4.093  34.636   1.506  1.00  0.80
ATOM    262  CA  GLY A  66       5.425  34.570   2.099  1.00  0.80
ATOM    263  C   GLY A  66       5.934  33.148   2.127  1.00  0.80
ATOM    264  O   GLY A  66       5.591  32.339   1.265  1.00  0.80
ATOM    265  N   PRO A  67       6.860  33.459   3.560  1.00  0.87
ATOM    266  CA  PRO A  67       7.570  32.183   3.556  1.00  0.87
ATOM    267  C   PRO A  67       6.935  31.209   4.520  1.00  0.87
ATOM    268  O   PRO A  67       6.552  31.580   5.629  1.00  0.87
ATOM    269  N   VAL A  68       6.843  30.047   4.101  1.00  0.89
ATOM    270  CA  VAL A  68       6.329  28.957   4.924  1.00  0.89
ATOM    271  C   VAL A  68       7.193  27.726   4.792  1.00  0.89
ATOM    272  O   VAL A  68       7.693  27.420   3.709  1.00  0.89
ATOM    273  N   THR A  69       7.391  27.023   5.807  1.00  0.92
ATOM    274  CA  THR A  69       8.265  25.854   5.767  1.00  0.92
ATOM    275  C   THR A  69       7.459  24.579   5.702  1.00  0.92
ATOM    276  O   THR A  69       6.564  24.357   6.517  1.00  0.92
ATOM    277  N   CYS A  70       7.815  23.780   4.720  1.00  0.85
ATOM    278  CA  CYS A  70       7.165  22.482   4.575  1.00  0.85
ATOM    279  C   CYS A  70       8.186  21.380   4.424  1.00  0.85
ATOM    280  O   CYS A  70       8.702  21.144   3.331  1.00  0.85
ATOM    281  N   GLY A  71       8.505  20.689   5.472  1.00  0.84
ATOM    282  CA  GLY A  71       9.569  19.691   5.422  1.00  0.84
ATOM    283  C   GLY A  71      10.909  20.342   5.177  1.00  0.84
ATOM    284  O   GLY A  71      11.355  21.180   5.960  1.00  0.84
ATOM    285  N   PRO A  72      11.615  20.113   4.252  1.00  0.84
ATOM    286  CA  PRO A  72      12.919  20.711   3.981  1.00  0.84
ATOM    287  C   PRO A  72      12.810  21.789   2.929  1.00  0.84
ATOM    288  O   PRO A  72      13.801  22.153   2.295  1.00  0.84
ATOM    289  N   TYR A  73      11.730  22.195   2.819  1.00  0.87
ATOM    290  CA  TYR A  73      11.438  23.175   1.777  1.00  0.87
ATOM    291  C   TYR A  73      10.813  24.418   2.364  1.00  0.87
ATOM    292  O   TYR A  73      10.085  24.349   3.354  1.00  0.87
ATOM    293  N   THR A  74      11.096  25.533   1.759  1.00  0.89
ATOM    294  CA  THR A  74      10.483  26.797   2.157  1.00  0.89
ATOM    295  C   THR A  74       9.756  27.434   0.997  1.00  0.89
ATOM    296  O   THR A  74      10.287  27.515  -0.111  1.00  0.89
ATOM    297  N   ILE A  75       8.600  27.872   1.211  1.00  0.89
ATOM    298  CA  ILE A  75       7.788  28.443   0.141  1.00  0.89
ATOM    299  C   ILE A  75       7.410  29.871   0.451  1.00  0.89
ATOM    300  O   ILE A  75       7.118  30.210   1.598  1.00  0.89
ATOM    301  N   THR A  76       7.423  30.688  -0.580  1.00  0.84
ATOM    302  CA  THR A  76       7.010  32.082  -0.451  1.00  0.84
ATOM    303  C   THR A  76       6.273  32.543  -1.686  1.00  0.84
ATOM    304  O   THR A  76       6.461  31.997  -2.773  1.00  0.84
ATOM    305  N   SER A  77       5.501  33.461  -1.558  1.00  0.82
ATOM    306  CA  SER A  77       4.719  33.933  -2.696  1.00  0.82
ATOM    307  C   SER A  77       4.587  35.437  -2.676  1.00  0.82
ATOM    308  O   SER A  77       4.902  36.083  -1.677  1.00  0.82
ATOM    309  N   SER A  78       4.081  35.890  -3.915  1.00  0.81
ATOM    310  CA  SER A  78       3.795  37.311  -4.082  1.00  0.81
ATOM    311  C   SER A  78       2.805  37.536  -5.201  1.00  0.81
ATOM    312  O   SER A  78       2.658  36.696  -6.089  1.00  0.81
ATOM    313  N   TRP A  79       2.235  38.533  -5.129  1.00  0.80
ATOM    314  CA  TRP A  79       1.212  38.837  -6.125  1.00  0.80
ATOM    315  C   TRP A  79       1.601  40.042  -6.949  1.00  0.80
ATOM    316  O   TRP A  79       2.292  40.939  -6.466  1.00  0.80
ATOM    317  N   SER A  80       1.117  39.927  -8.091  1.00  0.75
ATOM    318  CA  SER A  80       1.257  41.096  -8.953  1.00  0.75
ATOM    319  C   SER A  80      -0.093  41.602  -9.403  1.00  0.75
ATOM    320  O   SER A  80      -1.009  40.817  -9.648  1.00  0.75
ATOM    321  N   GLY A  81      -0.271  42.503  -9.506  1.00  0.71
ATOM    322  CA  GLY A  81      -1.592  43.101  -9.678  1.00  0.71
ATOM    323  C   GLY A  81      -1.631  43.981 -10.904  1.00  0.71
ATOM    324  O   GLY A  81      -2.615  44.680 -11.147  1.00  0.71
ATOM    325  N   GLN A  82      -0.688  43.888 -11.494  1.00  0.69
ATOM    326  CA  GLN A  82      -0.509  44.631 -12.738  1.00  0.69
ATOM    327  C   GLN A  82      -1.585  44.279 -13.737  1.00  0.69
ATOM    328  O   GLN A  82      -1.923  45.081 -14.608  1.00  0.69
ATOM    329  N   PHE A  83      -2.070  43.197 -13.625  1.00  0.69
ATOM    330  CA  PHE A  83      -3.076  42.721 -14.571  1.00  0.69
ATOM    331  C   PHE A  83      -4.443  42.681 -13.932  1.00  0.69
ATOM    332  O   PHE A  83      -5.433  42.345 -14.582  1.00  0.69
ATOM    333  N   GLY A  84      -4.581  43.015 -12.647  1.00  0.68
ATOM    334  CA  GLY A  84      -5.841  43.019 -11.909  1.00  0.68
ATOM    335  C   GLY A  84      -6.074  41.689 -11.232  1.00  0.68
ATOM    336  O   GLY A  84      -5.426  40.694 -11.557  1.00  0.68
ATOM    337  N   PRO A  85      -6.919  41.673 -10.374  1.00  0.73
ATOM    338  CA  PRO A  85      -7.166  40.449  -9.618  1.00  0.73
ATOM    339  C   PRO A  85      -7.561  39.317 -10.536  1.00  0.73
ATOM    340  O   PRO A  85      -6.834  38.333 -10.674  1.00  0.73
ATOM    341  N   ASN A  86      -8.556  39.407 -11.097  1.00  0.67
ATOM    342  CA  ASN A  86      -9.006  38.323 -11.966  1.00  0.67
ATOM    343  C   ASN A  86      -7.965  38.001 -13.012  1.00  0.67
ATOM    344  O   ASN A  86      -8.010  36.944 -13.640  1.00  0.67
ATOM    345  N   ASN A  87      -7.097  38.872 -13.165  1.00  0.73
ATOM    346  CA  ASN A  87      -6.091  38.696 -14.208  1.00  0.73
ATOM    347  C   ASN A  87      -4.704  38.623 -13.613  1.00  0.73
ATOM    348  O   ASN A  87      -3.769  38.143 -14.254  1.00  0.73
ATOM    349  N   GLY A  88      -4.608  39.070 -12.476  1.00  0.75
ATOM    350  CA  GLY A  88      -3.371  39.040 -11.701  1.00  0.75
ATOM    351  C   GLY A  88      -2.797  37.645 -11.652  1.00  0.75
ATOM    352  O   GLY A  88      -3.363  36.710 -12.220  1.00  0.75
ATOM    353  N   PHE A  89      -1.678  37.663 -10.942  1.00  0.76
ATOM    354  CA  PHE A  89      -0.970  36.388 -10.862  1.00  0.76
ATOM    355  C   PHE A  89      -0.226  36.264  -9.554  1.00  0.76
ATOM    356  O   PHE A  89       0.268  37.254  -9.014  1.00  0.76
ATOM    357  N   THR A  90      -0.162  35.072  -9.081  1.00  0.79
ATOM    358  CA  THR A  90       0.603  34.779  -7.873  1.00  0.79
ATOM    359  C   THR A  90       1.831  33.961  -8.195  1.00  0.79
ATOM    360  O   THR A  90       1.757  32.978  -8.932  1.00  0.79
ATOM    361  N   THR A  91       2.885  34.373  -7.656  1.00  0.79
ATOM    362  CA  THR A  91       4.140  33.670  -7.904  1.00  0.79
ATOM    363  C   THR A  91       4.632  32.984  -6.652  1.00  0.79
ATOM    364  O   THR A  91       4.630  33.571  -5.570  1.00  0.79
ATOM    365  N   PHE A  92       5.025  31.834  -6.772  1.00  0.81
ATOM    366  CA  PHE A  92       5.506  31.043  -5.642  1.00  0.81
ATOM    367  C   PHE A  92       6.939  30.617  -5.852  1.00  0.81
ATOM    368  O   PHE A  92       7.314  30.178  -6.939  1.00  0.81
ATOM    369  N   ALA A  93       7.720  30.731  -4.875  1.00  0.82
ATOM    370  CA  ALA A  93       9.118  30.313  -4.935  1.00  0.82
ATOM    371  C   ALA A  93       9.402  29.232  -3.920  1.00  0.82
ATOM    372  O   ALA A  93       9.207  29.427  -2.721  1.00  0.82
ATOM    373  N   VAL A  94       9.834  28.177  -4.406  1.00  0.83
ATOM    374  CA  VAL A  94      10.163  27.068  -3.514  1.00  0.83
ATOM    375  C   VAL A  94      11.658  26.877  -3.418  1.00  0.83
ATOM    376  O   VAL A  94      12.346  26.775  -4.433  1.00  0.83
ATOM    377  N   THR A  95      12.201  26.823  -2.249  1.00  0.82
ATOM    378  CA  THR A  95      13.637  26.679  -2.028  1.00  0.82
ATOM    379  C   THR A  95      13.934  25.461  -1.186  1.00  0.82
ATOM    380  O   THR A  95      13.362  25.283  -0.111  1.00  0.82
ATOM    381  N   ASP A  96      14.772  24.716  -1.683  1.00  0.77
ATOM    382  CA  ASP A  96      15.198  23.558  -0.902  1.00  0.77
ATOM    383  C   ASP A  96      16.515  23.827  -0.213  1.00  0.77
ATOM    384  O   ASP A  96      17.500  24.190  -0.856  1.00  0.77
ATOM    385  N   PHE A  97      16.485  23.669   0.847  1.00  0.74
ATOM    386  CA  PHE A  97      17.638  24.094   1.636  1.00  0.74
ATOM    387  C   PHE A  97      18.717  23.037   1.628  1.00  0.74
ATOM    388  O   PHE A  97      19.906  23.352   1.658  1.00  0.74
ATOM    389  N   SER A  98      18.416  21.872   1.591  1.00  0.73
ATOM    390  CA  SER A  98      19.371  20.771   1.672  1.00  0.73
ATOM    391  C   SER A  98      20.140  20.627   0.380  1.00  0.73
ATOM    392  O   SER A  98      21.292  20.194   0.378  1.00  0.73
ATOM    393  N   LYS A  99      19.583  20.959  -0.719  1.00  0.70
ATOM    394  CA  LYS A  99      20.206  20.809  -2.031  1.00  0.70
ATOM    395  C   LYS A  99      20.493  22.156  -2.649  1.00  0.70
ATOM    396  O   LYS A  99      21.187  22.250  -3.662  1.00  0.70
ATOM    397  N   LYS A 100      19.979  23.274  -2.077  1.00  0.73
ATOM    398  CA  LYS A 100      20.223  24.611  -2.611  1.00  0.73
ATOM    399  C   LYS A 100      19.571  24.780  -3.963  1.00  0.73
ATOM    400  O   LYS A 100      20.163  25.349  -4.880  1.00  0.73
ATOM    401  N   LEU A 101      18.470  24.341  -4.092  1.00  0.77
ATOM    402  CA  LEU A 101      17.674  24.396  -5.315  1.00  0.77
ATOM    403  C   LEU A 101      16.500  25.331  -5.153  1.00  0.77
ATOM    404  O   LEU A 101      16.067  25.611  -4.035  1.00  0.77
ATOM    405  N   ILE A 102      15.986  25.814  -6.288  1.00  0.77
ATOM    406  CA  ILE A 102      14.849  26.730  -6.245  1.00  0.77
ATOM    407  C   ILE A 102      13.931  26.506  -7.422  1.00  0.77
ATOM    408  O   ILE A 102      14.386  26.243  -8.535  1.00  0.77
ATOM    409  N   VAL A 103      12.619  26.607  -7.192  1.00  0.77
ATOM    410  CA  VAL A 103      11.606  26.557  -8.242  1.00  0.77
ATOM    411  C   VAL A 103      10.637  27.708  -8.115  1.00  0.77
ATOM    412  O   VAL A 103      10.384  28.199  -7.015  1.00  0.77
ATOM    413  N   TRP A 104      10.134  28.108  -9.149  1.00  0.74
ATOM    414  CA  TRP A 104       9.227  29.251  -9.103  1.00  0.74
ATOM    415  C   TRP A 104       8.142  29.122 -10.145  1.00  0.74
ATOM    416  O   TRP A 104       8.415  29.153 -11.345  1.00  0.74
ATOM    417  N   PRO A 105       6.968  28.983  -9.627  1.00  0.76
ATOM    418  CA  PRO A 105       5.865  28.914 -10.581  1.00  0.76
ATOM    419  C   PRO A 105       4.899  30.056 -10.373  1.00  0.76
ATOM    420  O   PRO A 105       4.900  30.699  -9.324  1.00  0.76
ATOM    421  N   ALA A 106       4.129  30.256 -11.363  1.00  0.78
ATOM    422  CA  ALA A 106       3.134  31.321 -11.286  1.00  0.78
ATOM    423  C   ALA A 106       1.772  30.820 -11.704  1.00  0.78
ATOM    424  O   ALA A 106       1.657  29.982 -12.599  1.00  0.78
ATOM    425  N   TYR A 107       0.847  31.375 -11.021  1.00  0.76
ATOM    426  CA  TYR A 107      -0.521  30.988 -11.356  1.00  0.76
ATOM    427  C   TYR A 107      -1.430  32.193 -11.394  1.00  0.76
ATOM    428  O   TYR A 107      -1.123  33.232 -10.810  1.00  0.76
ATOM    429  N   THR A 108      -2.467  32.016 -12.051  1.00  0.74
ATOM    430  CA  THR A 108      -3.451  33.091 -12.134  1.00  0.74
ATOM    431  C   THR A 108      -4.518  32.930 -11.077  1.00  0.74
ATOM    432  O   THR A 108      -4.827  31.815 -10.659  1.00  0.74
ATOM    433  N   ASP A 109      -5.015  33.985 -10.703  1.00  0.75
ATOM    434  CA  ASP A 109      -6.062  33.993  -9.685  1.00  0.75
ATOM    435  C   ASP A 109      -7.278  33.230 -10.155  1.00  0.75
ATOM    436  O   ASP A 109      -7.847  32.432  -9.411  1.00  0.75
ATOM    437  N   VAL A 110      -7.594  33.459 -11.210  1.00  0.74
ATOM    438  CA  VAL A 110      -8.739  32.760 -11.786  1.00  0.74
ATOM    439  C   VAL A 110      -8.548  31.264 -11.719  1.00  0.74
ATOM    440  O   VAL A 110      -9.516  30.503 -11.736  1.00  0.74
ATOM    441  N   GLN A 111      -7.307  30.895 -11.644  1.00  0.74
ATOM    442  CA  GLN A 111      -6.997  29.469 -11.634  1.00  0.74
ATOM    443  C   GLN A 111      -7.149  28.893 -10.246  1.00  0.74
ATOM    444  O   GLN A 111      -7.373  27.693 -10.083  1.00  0.74
ATOM    445  N   VAL A 112      -7.049  29.640  -9.236  1.00  0.73
ATOM    446  CA  VAL A 112      -7.086  29.145  -7.863  1.00  0.73
ATOM    447  C   VAL A 112      -8.397  29.491  -7.199  1.00  0.73
ATOM    448  O   VAL A 112      -8.901  28.735  -6.367  1.00  0.73
ATOM    449  N   GLN A 113      -9.025  30.535  -7.453  1.00  0.69
ATOM    450  CA  GLN A 113     -10.269  31.011  -6.854  1.00  0.69
ATOM    451  C   GLN A 113     -11.222  29.866  -6.607  1.00  0.69
ATOM    452  O   GLN A 113     -11.116  28.811  -7.232  1.00  0.69
ATOM    453  N   ALA A 114     -12.082  30.103  -5.743  1.00  0.67
ATOM    454  CA  ALA A 114     -13.148  29.172  -5.387  1.00  0.67
ATOM    455  C   ALA A 114     -12.579  27.865  -4.886  1.00  0.67
ATOM    456  O   ALA A 114     -13.319  26.922  -4.606  1.00  0.67
ATOM    457  N   GLY A 115     -11.379  27.858  -4.799  1.00  0.65
ATOM    458  CA  GLY A 115     -10.905  26.601  -4.226  1.00  0.65
ATOM    459  C   GLY A 115     -10.639  25.581  -5.308  1.00  0.65
ATOM    460  O   GLY A 115     -10.534  24.386  -5.034  1.00  0.65
ATOM    461  N   LYS A 116     -10.541  26.074  -6.475  1.00  0.68
ATOM    462  CA  LYS A 116     -10.314  25.112  -7.550  1.00  0.68
ATOM    463  C   LYS A 116      -8.854  25.061  -7.929  1.00  0.68
ATOM    464  O   LYS A 116      -8.252  26.084  -8.258  1.00  0.68
ATOM    465  N   VAL A 117      -8.490  24.072  -7.863  1.00  0.65
ATOM    466  CA  VAL A 117      -7.104  23.782  -8.219  1.00  0.65
ATOM    467  C   VAL A 117      -6.856  24.046  -9.685  1.00  0.65
ATOM    468  O   VAL A 117      -7.784  24.034 -10.493  1.00  0.65
ATOM    469  N   VAL A 118      -5.755  24.226  -9.798  1.00  0.65
ATOM    470  CA  VAL A 118      -5.334  24.414 -11.183  1.00  0.65
ATOM    471  C   VAL A 118      -4.432  23.289 -11.631  1.00  0.65
ATOM    472  O   VAL A 118      -3.733  22.682 -10.821  1.00  0.65
ATOM    473  N   SER A 119      -4.833  23.499 -12.702  1.00  0.62
ATOM    474  CA  SER A 119      -4.256  22.574 -13.673  1.00  0.62
ATOM    475  C   SER A 119      -3.897  23.290 -14.953  1.00  0.62
ATOM    476  O   SER A 119      -4.766  23.588 -15.773  1.00  0.62
ATOM    477  N   PRO A 120      -2.902  23.470 -15.022  1.00  0.57
ATOM    478  CA  PRO A 120      -2.287  22.146 -14.996  1.00  0.57
ATOM    479  C   PRO A 120      -1.511  21.937 -13.717  1.00  0.57
ATOM    480  O   PRO A 120      -0.426  22.491 -13.540  1.00  0.57
ATOM    481  N   ASN A 121      -2.013  21.088 -12.675  1.00  0.67
ATOM    482  CA  ASN A 121      -0.854  20.540 -11.978  1.00  0.67
ATOM    483  C   ASN A 121       0.428  20.921 -12.679  1.00  0.67
ATOM    484  O   ASN A 121       0.580  20.695 -13.880  1.00  0.67
ATOM    485  N   GLN A 122       1.211  21.419 -12.007  1.00  0.71
ATOM    486  CA  GLN A 122       2.331  22.014 -12.731  1.00  0.71
ATOM    487  C   GLN A 122       3.649  21.498 -12.205  1.00  0.71
ATOM    488  O   GLN A 122       3.828  21.345 -10.996  1.00  0.71
ATOM    489  N   SER A 123       4.513  21.260 -13.229  1.00  0.71
ATOM    490  CA  SER A 123       5.824  20.741 -12.851  1.00  0.71
ATOM    491  C   SER A 123       6.929  21.589 -13.432  1.00  0.71
ATOM    492  O   SER A 123       6.789  22.148 -14.520  1.00  0.71
ATOM    493  N   TYR A 124       7.916  21.618 -12.685  1.00  0.74
ATOM    494  CA  TYR A 124       9.025  22.438 -13.164  1.00  0.74
ATOM    495  C   TYR A 124      10.346  21.911 -12.656  1.00  0.74
ATOM    496  O   TYR A 124      10.410  21.291 -11.595  1.00  0.74
ATOM    497  N   ALA A 125      11.324  22.171 -13.413  1.00  0.73
ATOM    498  CA  ALA A 125      12.664  21.772 -12.994  1.00  0.73
ATOM    499  C   ALA A 125      13.298  22.834 -12.128  1.00  0.73
ATOM    500  O   ALA A 125      13.116  24.029 -12.362  1.00  0.73
ATOM    501  N   PRO A 126      13.896  22.446 -11.327  1.00  0.73
ATOM    502  CA  PRO A 126      14.551  23.333 -10.371  1.00  0.73
ATOM    503  C   PRO A 126      15.810  23.924 -10.957  1.00  0.73
ATOM    504  O   PRO A 126      16.352  23.409 -11.935  1.00  0.73
ATOM    505  N   ALA A 127      16.114  24.955 -10.260  1.00  0.72
ATOM    506  CA  ALA A 127      17.379  25.612 -10.576  1.00  0.72
ATOM    507  C   ALA A 127      18.368  25.453  -9.447  1.00  0.72
ATOM    508  O   ALA A 127      17.982  25.323  -8.285  1.00  0.72
ATOM    509  N   ASN A 128      19.479  25.458  -9.706  1.00  0.69
ATOM    510  CA  ASN A 128      20.491  25.310  -8.665  1.00  0.69
ATOM    511  C   ASN A 128      21.087  26.647  -8.296  1.00  0.69
ATOM    512  O   ASN A 128      21.309  27.498  -9.158  1.00  0.69
ATOM    513  N   LEU A 129      21.269  26.699  -7.174  1.00  0.66
ATOM    514  CA  LEU A 129      21.923  27.910  -6.687  1.00  0.66
ATOM    515  C   LEU A 129      23.390  27.665  -6.427  1.00  0.66
ATOM    516  O   LEU A 129      23.776  26.594  -5.957  1.00  0.66
ATOM    517  N   PRO A 130      24.015  28.544  -6.707  1.00  0.56
ATOM    518  CA  PRO A 130      25.442  28.397  -6.436  1.00  0.56
ATOM    519  C   PRO A 130      25.729  28.541  -4.960  1.00  0.56
ATOM    520  O   PRO A 130      24.912  29.072  -4.209  1.00  0.56
ATOM    521  N   LEU A 131      26.739  28.127  -4.620  1.00  0.51
ATOM    522  CA  LEU A 131      27.018  28.170  -3.188  1.00  0.51
ATOM    523  C   LEU A 131      28.417  28.674  -2.924  1.00  0.51
ATOM    524  O   LEU A 131      29.164  28.972  -3.855  1.00  0.51
ATOM    525  N   GLU A 132      28.575  28.698  -1.738  1.00  0.42
ATOM    526  CA  GLU A 132      29.816  29.269  -1.223  1.00  0.42
ATOM    527  C   GLU A 132      30.621  28.231  -0.478  1.00  0.42
ATOM    528  O   GLU A 132      31.813  28.414  -0.233  1.00  0.42
ATOM    529  N   HIS A 133      29.884  27.161  -0.154  1.00  0.35
ATOM    530  CA  HIS A 133      30.549  25.994   0.419  1.00  0.35
ATOM    531  C   HIS A 133      30.602  26.086   1.925  1.00  0.35
ATOM    532  O   HIS A 133      30.021  25.259   2.628  1.00  0.35
ATOM    533  N   HIS A 134      31.290  27.083   2.393  1.00  0.31
ATOM    534  CA  HIS A 134      31.490  27.166   3.837  1.00  0.31
ATOM    535  C   HIS A 134      31.945  25.840   4.396  1.00  0.31
ATOM    536  O   HIS A 134      32.112  25.690   5.607  1.00  0.31
ATOM    537  N   HIS A 135      32.107  24.968   3.396  1.00  0.24
ATOM    538  CA  HIS A 135      32.345  23.537   3.553  1.00  0.24
ATOM    539  C   HIS A 135      31.097  22.744   3.243  1.00  0.24
ATOM    540  O   HIS A 135      31.119  21.513   3.233  1.00  0.24
ATOM    541  N   HIS A 136      30.131  23.573   3.021  1.00  0.24
ATOM    542  CA  HIS A 136      28.740  23.136   3.096  1.00  0.24
ATOM    543  C   HIS A 136      28.337  22.858   4.524  1.00  0.24
ATOM    544  O   HIS A 136      29.178  22.832   5.423  1.00  0.24
ATOM    545  N   HIS A 137      27.060  22.651   4.744  1.00  0.29
ATOM    546  CA  HIS A 137      26.503  22.696   6.093  1.00  0.29
ATOM    547  C   HIS A 137      25.128  22.075   6.131  1.00  0.29
ATOM    548  O   HIS A 137      24.882  21.135   6.887  1.00  0.29
ATOM    549  N   HIS A 138      24.194  22.576   5.322  1.00  0.24
ATOM    550  CA  HIS A 138      22.820  22.089   5.253  1.00  0.24
ATOM    551  C   HIS A 138      21.891  22.977   6.046  1.00  0.24
ATOM    552  O   HIS A 138      22.004  23.074   7.268  1.00  0.24
```
