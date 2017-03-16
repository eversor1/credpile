# CredPile

### Linux install-time dependencies
CredPile recently moved from PyCrypto to `cryptography`. `cryptography` uses pre-built binary wheels on OSX and Windows, but does not on Linux. That means that you need to install some dependencies if you want to run credpile on linux. 

For Debian and Ubuntu, the following command will ensure that the required dependencies are installed:
```
$ sudo apt-get install build-essential libssl-dev libffi-dev python-dev
```
For Fedora and RHEL-derivatives, the following command will ensure that the required dependencies are installed:
```
$ sudo yum install gcc libffi-devel python-devel openssl-devel
```

See https://cryptography.io/en/latest/installation/ for more information.


## What is this?
Software systems often need access to some shared credential. For example, your web application needs access to a database password, or an API key for some third party service.

Some organizations build complete credential-management systems, but for most of us, managing these credentials is usually an afterthought. In the best case, people use systems like ansible-vault, which does a pretty good job, but leads to other management issues (like where/how to store the master key). A lot of credential management schemes amount to just SCP'ing a `secrets` file out to the fleet, or in the worst case, burning secrets into the SCM (do a github search on `password`).

CredPile is a very simple, easy to use credential management and distribution system that uses AWS Key Management Service (KMS) for key wrapping and master-key storage, and S3 for credential storage and sharing.


## How does it work?
After you complete the steps in the `Setup` section, you will have an encryption key in KMS (in this README, we will refer to that key as the `master key`), and a credential storage file in S3.

### Stashing Secrets
Whenever you want to store/share a credential, such as a database password, you simply run `credpile put [credential-name] [credential-value]`. For example, `credpile put myapp.db.prod supersecretpassword1234`. credpile will go to the KMS and generate a unique data encryption key, which itself is encrypted by the master key (this is called key wrapping). credpile will use the data encryption key to encrypt the credential value. It will then store the encrypted credential, along with the wrapped (encrypted) data encryption key in the credential store in S3.

### Getting Secrets
When you want to fetch the credential, for example as part of the bootstrap process on your web-server, you simply do `credpile get [credential-name]`. For example, `export DB_PASSWORD=$(credpile get myapp.db.prod)`. When you run `get`, credpile will go and fetch the encrypted credential and the wrapped encryption key from the credential store (S3). It will then send the wrapped encryption key to KMS, where it is decrypted with the master key. credpile then uses the decrypted data encryption key to decrypt the credential. The credential is printed to `stdout`, so you can use it in scripts or assign it to environment variables.

### Controlling and Auditing Secrets
Optionally, you can include any number of [Encryption Context](http://docs.aws.amazon.com/kms/latest/developerguide/encrypt-context.html) key value pairs to associate with the credential. The exact set of encryption context key value pairs that were associated with the credential when it was `put` in S3 must be provided in the `get` request to successfully decrypt the credential. These encryption context key value pairs are useful to provide auditing context to the encryption and decryption operations in your CloudTrail logs. They are also useful for constraining access to a given credpile stored credential by using KMS Key Policy conditions and KMS Grant conditions. Doing so allows you to, for example, make sure that your database servers and web-servers can read the web-server DB user password but your database servers can not read your web-servers TLS/SSL certificate's private key. A `put` request with encryption context would look like `credpile put myapp.db.prod supersecretpassword1234 app.tier=db environment=prod`. In order for your web-servers to read that same credential they would execute a `get` call like `export DB_PASSWORD=$(credpile get myapp.db.prod environment=prod app.tier=db)`

### Versioning Secrets
Credentials stored in the credential-store are versioned and immutable. That is, if you `put` a credential called `foo` with a version of `1` and a value of `bar`, then foo version 1 will always have a value of bar, and there is no way in `credpile` to change its value (although you could go fiddle with the files in S3, but you shouldn't do that). Credential rotation is handed through versions. Suppose you do `credpile put foo bar`, and then decide later to rotate `foo`, you can put version 2 of `foo` by doing `credpile put foo baz -v `. The next time you do `credpile get foo`, it will return `baz`. You can get specific credential versions as well (with the same `-v` flag). You can fetch a list of all credentials in the credential-store and their versions with the `list` command.

## Dependencies
credpile uses the following AWS services:
* AWS Key Management Service (KMS) - for master key management and key wrapping
* AWS Identity and Access Management - for access control
* Amazon S3 - for credential storage

## Setup
### tl;dr
1. Set up a key called `credpile` in KMS
2. Install credpile's python dependencies (or just use pip)
3. Make sure you have AWS creds in a place that boto/botocore can read them
4. Run `credpile setup`

### Setting up KMS
`credpile` will not currently set up your KMS master key. To create a KMS master key,

1. Go to the AWS console
2. Go to the IAM console/tab
3. Click "Encryption Keys" in the left
4. Click "Create Key". For alias, put "credpile". If you want to use a different name, be sure to pass it to credpile with the `-k` flag
5. Decide what IAM principals you want to be able to manage the key
6. On the "Key Usage Permissions" screen, pick the IAM users/roles that will be using credpile (you can change your mind later)
7. Done!


The python dependencies for credpile are in the `requirements.txt` file. You can install them with `pip install -r requirements.txt`.

In all cases, you will need a C compiler for building `PyCrypto` (you can install `gcc` by doing `apt-get install gcc` or `yum install gcc`).

You will need to have AWS credentials accessible to boto/botocore. The easiest thing to do is to run credpile on an EC2 instance with an IAM role. Alternatively, you can put AWS credentials in the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` environment variables. Or, you can put them in a file (see http://boto.readthedocs.org/en/latest/boto_config_tut.html).

You can specify the region in which `credpile` should operate by using the `-r` flag, or by setting the `AWS_DEFAULT_REGION` environment variable. Note that the command line flag takes precedence over the environment variable. If you set neither, then `credpile` will operate against us-east-1.

### Working with multiple AWS accounts (profiles)

If you need to work with multiple AWS accounts, an easy thing to do is to set up multiple profiles in your `~/.aws/credentials` file. For example,

```
[dev]
aws_access_key_id = AKIDEXAMPLEASDFASDF
aws_secret_access_key = SKIDEXAMPLE2103429812039423
[prod]
aws_access_key_id= AKIDEXAMPLEASDFASDF
aws_secret_access_key= SKIDEXAMPLE2103429812039423
```

Then, by setting the `AWS_PROFILE` environment variable to the name of the profile, (dev or prod, in this case), you can point credpile at the appropriate account.

See https://blogs.aws.amazon.com/security/post/Tx3D6U6WSFGOK2H/A-New-and-Standardized-Way-to-Manage-Credentials-in-the-AWS-SDKs for more information.

## Usage
```
usage: credpile [-h] [-r REGION] [-b BUCKET] [-P PATH] {delete,get,getall,list,put,setup} ...

A credential/secret storage system

delete
    usage: credpile delete [-h] [-r REGION] [-b BUCKET] [-P PATH] credential

    positional arguments:
      credential  the name of the credential to delete

get
    usage: credpile get [-h] [-r REGION] [-b BUCKET] [-P PATH] [-k KEY] [-n] [-v VERSION]
                         credential [context [context ...]]

    positional arguments:
      credential            the name of the credential to get. Using the wildcard
                            character '*' will search for credentials that match
                            the pattern
      context               encryption context key/value pairs associated with the
                            credential in the form of "key=value"

    optional arguments:
      -n, --noline          Don't append newline to returned value (useful in
                            scripts or with binary files)
      -v VERSION, --version VERSION
                            Get a specific version of the credential (defaults to
                            the latest version).

getall
    usage: credpile getall [-h] [-r REGION] [-b BUCKET] [-P PATH] [-v VERSION] [-f {json,yaml,csv}]
                            [context [context ...]]

    positional arguments:
      context               encryption context key/value pairs associated with the
                            credential in the form of "key=value"

    optional arguments:
      -v VERSION, --version VERSION
                            Get a specific version of the credential (defaults to
                            the latest version).
      -f {json,yaml,csv}, --format {json,yaml,csv}
                            Output format. json(default), yaml or csv.


list
    usage: credpile list [-h] [-r REGION] [-b BUCKET] [-P PATH]

put
usage: credpile put [-h] [-k KEY] [-v VERSION] [-b BUCKET] [-P PATH] [-a]
                     credential value [context [context ...]]

positional arguments:
  credential            the name of the credential to store
  value                 the value of the credential to store or, if beginning
                        with the "@" character, the filename of the file
                        containing the value
  context               encryption context key/value pairs associated with the
                        credential in the form of "key=value"

optional arguments:
  -h, --help            show this help message and exit
  -k KEY, --key KEY     the KMS key-id of the master key to use. See the
                        README for more information. Defaults to
                        alias/credpile
  -v VERSION, --version VERSION
                        Put a specific version of the credential (update the
                        credential; defaults to version `1`).
  -a, --autoversion     Automatically increment the version of the credential
                        to be stored. This option causes the `-v` flag to be
                        ignored. (This option will fail if the currently
                        stored version is not numeric.)

setup
    usage: credpile setup [-h] [-r REGION] [-b BUCKET] [-P PATH]

optional arguments:
  -r REGION, --region REGION
                        the AWS region in which to operate. If a region is not
                        specified, credpile will use the value of the
                        AWS_DEFAULT_REGION env variable, or if that is not
                        set, us-east-1
  -b BUCKET, --bucket BUCKET 
                        S3 Bucket name to use for credential storage
  -P PATH, --path PATH
			Path within the S3 Bucket to use for credential storage
			and retrieval
  -n ARN, --arn ARN     AWS IAM ARN for AssumeRole
```
## IAM Policies

### Secret Writer
You can put or write secrets to credpile by either using KMS Key Grants, KMS Key Policies, or IAM Policies. If you are using IAM Policies, the following IAM permissions are the minimum required to be able to put or write secrets:
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "kms:GenerateDataKey"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:kms:us-east-1:AWSACCOUNTID:key/KEY-GUID"
    },
    {
      "Action": [
        "dynamodb:PutItem"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:dynamodb:us-east-1:AWSACCOUNTID:table/credential-store"
    }
  ]
}
```
If you are using Key Policies or Grants, then the `kms:GenerateDataKey` is not required in the policy for the IAM user/group/role. Replace `AWSACCOUNTID` with the account ID for your table, and replace the KEY-GUID with the identifier for your KMS key (which you can find in the KMS console).

### Secret Reader
You can read secrets from credpile with the get or getall actions by either using KMS Key Grants, KMS Key Policies, or IAM Policies. If you are using IAM Policies, the following IAM permissions are the minimum required to be able to get or read secrets:
```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "kms:Decrypt"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:kms:us-east-1:AWSACCOUNTID:key/KEY-GUID"
    },
    {
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query",
        "dynamodb:Scan"
      ],
      "Effect": "Allow",
      "Resource": "arn:aws:dynamodb:us-east-1:AWSACCOUNTID:table/credential-store"
    }
  ]
}
```
If you are using Key Policies or Grants, then the `kms:Decrypt` is not required in the policy for the IAM user/group/role. Replace `AWSACCOUNTID` with the account ID for your table, and replace the KEY-GUID with the identifier for your KMS key (which you can find in the KMS console). Note that the `dynamodb:Scan` permission is not required if you do not use wildcards in your `get`s.

## Security Notes
Any IAM principal who can get items from the credential store S3 Bucket, and can call KMS.Decrypt, can read stored credentials.

The target deployment-story for `credpile` is an EC2 instance running with an IAM role that has permissions to read the credential store and use the master key. Since IAM role credentials are vended by the instance metadata service, by default, any user on the system can fetch creds and use them to retrieve credentials. That means that by default, the instance boundary is the security boundary for this system. If you are worried about unauthorized users on your instance, you should take steps to secure access to the Instance Metadata Service (for example, use iptables to block connections to 169.254.169.254 except for privileged users). Also, because credpile is written in python, if an attacker can dump the memory of the credpile process, they may be able to recover credentials. This is a known issue, but again, in the target deployment case, the security boundary is assumed to be the instance boundary.


## Frequently Asked Questions (FAQ)

### 1. Where is the master key stored?
The master key is stored in AWS Key Management Service (KMS), where it is stored in secure HSM-backed storage. The Master Key never leaves the KMS service.

### 2. How is credential rotation handled?
Every credential in the store has a version number. Whenever you want to a credential to a new value, you have to do a `put` with a new credential version. For example, if you have `foo` version 1 in the database, then to update `foo`, you can put version 2. You can either specify the version manually (i.e. `credpile put foo bar -v 2`), or you can use the `-a` flag, which will attempt to autoincrement the version number (for example, `credpile put foo baz -a`). Whenever you do a `get` operation, credpile will fetch the most recent (highest version) version of that credential. So, to do credential rotation, simply put a new version of the credential, and clients fetching the credential will get the new version.
