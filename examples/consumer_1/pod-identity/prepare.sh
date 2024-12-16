#!/bin/sh -x

export REGION=us-east-1
export CLUSTER_NAME=luciano-eks-cluster-uno
export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export OIDC_PROVIDER=$(aws eks describe-cluster --name ${CLUSTER_NAME} --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")
export NAMESPACE=default
export SERVICE_ACCOUNT=spark-operator-spark


helm install spark-operator spark-operator/spark-operator \
    --namespace spark-operator \
    --create-namespace \
    --set webhook.enable=true

sleep 10
aws eks create-addon \
    --cluster-name ${CLUSTER_NAME} \
    --addon-name eks-pod-identity-agent \
    --region ${REGION}

cat >policy.json <<EOF
{
	"Version": "2012-10-17",
	"Statement": [
		{
			"Effect": "Allow",
			"Action": [
				"s3:*",
				"sqs:*"
			],
			"Resource": "*"
		}
	]
}
EOF
sleep 10
aws iam create-policy --policy-name FullS3SQSAccess --policy-document file://policy.json

cat >trust.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "pods.eks.amazonaws.com"
      },
      "Action": ["sts:AsumeRole","sts:TagSession"]
    }
  ]
}
EOF

sleep 30
aws iam create-role --role-name Spark-SQS-S3-Trust-Role-PodIdentity --assume-role-policy-document file://trust.json

sleep 15
aws eks create-pod-identity-association \
    --cluster-name ${CLUSTER_NAME} \
    --namespace ${NAMESPACE} \
    --service-account ${SERVICE_ACCOUNT} \
    --role-arn arn:aws:iam::${ACCOUNT_ID}:role/Spark-SQS-S3-Trust-Role-PodIdentity \
    --region ${REGION}

sleep 20
kubectl annotate serviceaccount -n $NAMESPACE $SERVICE_ACCOUNT eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/Spark-SQS-S3-Trust-Role-PodIdentity
