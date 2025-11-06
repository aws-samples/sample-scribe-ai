#!/bin/bash
# Remove set -e to prevent script from exiting on non-zero exit codes
set -e

export APP=$1
export ARCH=$2

export VERSION=$(cat /dev/urandom | LC_ALL=C tr -dc 'a-zA-Z0-9' | fold -w 50 | head -n 1)

# login to ECR
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REGISTRY=${ACCOUNT}.dkr.ecr.${AWS_REGION}.amazonaws.com
echo "logging into to ecr: ${REGISTRY}"
aws ecr get-login-password | docker login --username AWS --password-stdin ${REGISTRY}

# build and push image
IMAGE=${REGISTRY}/${APP}:${VERSION}
echo ""
echo "building and pushing image: ${IMAGE}"
docker build -t ${IMAGE} --platform ${ARCH} --provenance=false .
docker push ${IMAGE}

# deploy to lambda
echo ""
echo "updating lambda function (${APP}) with new image digest: ${IMAGE}"
aws lambda update-function-code --function-name ${APP} --image-uri ${IMAGE}
