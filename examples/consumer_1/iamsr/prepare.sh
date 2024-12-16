#!/bin/sh -x

export ACCOUNT_ID=$(aws sts get-caller-identity --query "Account" --output text)
export OIDC_PROVIDER=$(aws eks describe-cluster --name luciano-eks-cluster-uno --query "cluster.identity.oidc.issuer" --output text | sed -e "s/^https:\/\///")
export NAMESPACE=default
export SERVICE_ACCOUNT=spark-operator-spark

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

aws iam create-policy --policy-name FullS3SQSAccess --policy-document file://policy.json

sleep 30
cat >trust.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER}"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "${OIDC_PROVIDER}:aud": "sts.amazonaws.com",
          "${OIDC_PROVIDER}:sub": "system:serviceaccount:${NAMESPACE}:${SERVICE_ACCOUNT}"
        }
      }
    }
  ]
}
EOF

sleep 30
aws iam create-role --role-name Spark-SQS-S3-Trust-Role-IRSA --assume-role-policy-document file://trust.json

sleep 30
aws iam attach-role-policy --role-name Spark-SQS-S3-Trust-Role-IRSA --policy-arn arn:aws:iam::${ACCOUNT_ID}:policy/FullS3SQSAccess

sleep 30
kubectl annotate serviceaccount -n $NAMESPACE $SERVICE_ACCOUNT eks.amazonaws.com/role-arn=arn:aws:iam::${ACCOUNT_ID}:role/Spark-SQS-S3-Trust-Role-IRSA
