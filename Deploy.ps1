param(
    $Subscription = "48bbc269-ce89-4f6f-9a12-c6f91fcb772d",
    $ResourceGroup = "rosettafold3-rg",
    $Location = "eastus2"
)
az account set --subscription $Subscription
az group create -l $Location -n $ResourceGroup
az deployment group create -g $ResourceGroup -f azuredeploy.json -p "@azuredeploy.parameters.json"
