# Drain ECS instances on termination

This lambda function automates setting ECS instances to draining state using an auto scaling
lifecycle hook when instances are due to be terminated. 

Draining the instance prevents sudden loss of running tasks when an ECS instance is terminated.
Common scenarios are rolling AMI updates or autoscaling scale in operations. By draining the 
instance first, ECS relocates tasks on other instances and only terminates an instance when there
are no tasks running on it.

## Usage

The drainer is a standalone component deployable on its own. AN ECS cluster integrating with the drainer will need some additional resources provisioned. 
### Drainer Deployment

Deploy this lambda function with `sls deploy` (you'll need serverless framework from `npm i -g serverless`)

### ECS Cluster Deployment

To set this up for invocation by an auto scaling group lifecycle hook, provision the following resources along with your ECS cluster (given here as a CloudFormation snippet):

```yaml

Parameters:

  paramECSDrainerLambdaArn:
    Description: ARN for ECS drainer lambda function
    Type: String
    Default: ''
    # Set value to empty string to disable ECS drainer integration

Conditions:
  UseECSDrainer:
    !Not [!Equals [!Ref paramECSDrainerLambdaArn, '']]

Resources:
  #
  # ECS Drainer integration
  #
  AutoScalingNotificationRole:
    Type: "AWS::IAM::Role"
    Condition: UseECSDrainer
    Properties:
      AssumeRolePolicyDocument:
        Version: "2012-10-17"
        Statement:
          -
            Effect: "Allow"
            Principal:
              Service:
                - "autoscaling.amazonaws.com"
            Action:
              - "sts:AssumeRole"
      ManagedPolicyArns:
      - arn:aws:iam::aws:policy/service-role/AutoScalingNotificationAccessRole
      Path: "/"

  ASGSNSTopic:
    Type: "AWS::SNS::Topic"
    Condition: UseECSDrainer
    Properties:
      Subscription:
        -
          Endpoint: !Ref paramECSDrainerLambdaArn
          Protocol: "lambda"
      DisplayName: !Sub "ECS drainer autoscaling lifecycle hook notifications for ${ECSCluster}"

  ASGTerminateHook:
    Type: "AWS::AutoScaling::LifecycleHook"
    Condition: UseECSDrainer
    Properties:
      AutoScalingGroupName: !Ref ECSAutoScalingGroup
      DefaultResult: "ABANDON"
      HeartbeatTimeout: "900"
      LifecycleTransition: "autoscaling:EC2_INSTANCE_TERMINATING"
      NotificationTargetARN: !Ref ASGSNSTopic
      RoleARN: !GetAtt AutoScalingNotificationRole.Arn
    DependsOn: ASGSNSTopic

  LambdaInvokePermission:
    Type: "AWS::Lambda::Permission"
    Condition: UseECSDrainer
    Properties:
       FunctionName: !Ref paramECSDrainerLambdaArn
       Action: lambda:InvokeFunction
       Principal: "sns.amazonaws.com"
       SourceArn: !Ref ASGSNSTopic

```

Also make sure your ECS instances have a tag with key `ECSCluster` and the cluster name as the tag value. The drainer function will look up the cluster this way based on the EC2 instance id contained in the lifecycle hook notification message.

```yaml
  ECSAutoScalingGroup:
    Type: AWS::AutoScaling::AutoScalingGroup
    Properties:
      ...
      Tags:
        ...
        - Key: ECSCluster
          Value: !Ref ECSCluster
          PropagateAtLaunch: true
      ...
```