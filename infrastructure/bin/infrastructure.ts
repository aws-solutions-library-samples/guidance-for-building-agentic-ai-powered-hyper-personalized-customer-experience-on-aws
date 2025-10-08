#!/usr/bin/env node
import * as cdk from "aws-cdk-lib";
import { CxAppStack } from "../lib/infrastructure-stack";
import { AwsSolutionsChecks } from 'cdk-nag'
import { Aspects } from 'aws-cdk-lib';

const app = new cdk.App();
// cdk-nag AwsSolutions Pack with extra verbose logging enabled.
Aspects.of(app).add(new AwsSolutionsChecks({ verbose: true }))

// *****Important****** Do not change the name of the stack here. It will break the OpenSearch catalog loader script.
new CxAppStack(app, "CxHyperPersonalizeApp", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});