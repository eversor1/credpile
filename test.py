import boto3

client = boto3.client('s3')
try:
  contents = client.get_object(Bucket="credpile", Key="creds/nginx.cred")
  version = 0
  #creds = contents['Body'].read().splitlines()
  for cred in contents['Body'].read().splitlines():
    parts=cred.split('|')
    if int(parts[1]) > version:
      version = int(parts[1])
  print version
except:
  print 0
