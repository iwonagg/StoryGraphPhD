# JSON Validation API

## Azure functions

https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=v4%2Cmacos%2Ccsharp%2Cportal%2Cbash%2Ckeda

## Deployment

### Without custom image

```bash
az-mct
func azure functionapp publish story-graph
```

### Custom image

```bash
az-mct
az acr build --subscription e126996c-7c5a-4aef-a418-e4a545c0deca --registry navisborealis --image storygraph:v1 .
```

## Run locally

### Without custom image

```bash
func start
```

### Custom image

```bash
docker run -p 8080:80 -it navisborealis.azurecr.io/storygraph:v1
```