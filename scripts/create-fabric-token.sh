#!/bin/bash

az account get-access-token --resource https://database.windows.net --query accessToken -o tsv