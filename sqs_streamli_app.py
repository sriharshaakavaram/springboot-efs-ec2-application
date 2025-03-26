import streamlit as st
import subprocess
import json
import boto3
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session

# Config - Update these values
AWS_SIGNIN_HELPER_PATH = "/path/to/aws_signin_helper"
PROFILE_ARN = "arn:aws:iam::123456789012:role/YourIAMRole"
TRUST_ANCHOR_ARN = "arn:aws:rolesanywhere:us-east-1:123456789012:trust-anchor/abc123"
CERTIFICATE_PATH = "/path/to/certificate.pem"
PRIVATE_KEY_PATH = "/path/to/private.key"
SESSION_DURATION = "3600"

# Auth
def get_temp_credentials():
    if 'aws_credentials' in st.session_state:
        return st.session_state['aws_credentials']
    cmd = [
        AWS_SIGNIN_HELPER_PATH, "credential-process",
        "--certificate", CERTIFICATE_PATH,
        "--private-key", PRIVATE_KEY_PATH,
        "--trust-anchor-arn", TRUST_ANCHOR_ARN,
        "--profile-arn", PROFILE_ARN,
        "--duration", SESSION_DURATION
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise Exception(f"Credential Error: {result.stderr}")
    creds = json.loads(result.stdout)
    st.session_state['aws_credentials'] = creds
    return creds

def refreshable_boto3_client(service):
    creds = get_temp_credentials()
    def refresh():
        return {
            'access_key': creds['AccessKeyId'],
            'secret_key': creds['SecretAccessKey'],
            'token': creds['SessionToken'],
            'expiry_time': creds['Expiration']
        }
    session_credentials = RefreshableCredentials.create_from_metadata(
        metadata=refresh(),
        refresh_using=refresh,
        method='sts-assume-role'
    )
    session = get_session()
    session._credentials = session_credentials
    authed_session = boto3.Session(botocore_session=session)
    return authed_session.client(service)

# Load SQS client
try:
    sqs_client = refreshable_boto3_client("sqs")
except Exception as e:
    st.error(f"Authentication failed: {e}")
    st.stop()

st.title("AWS SQS Manager (IAM Roles Anywhere)")

# --- Queue Creation ---
with st.expander("Create New Queue"):
    new_queue_name = st.text_input("Queue Name")
    is_fifo = st.checkbox("FIFO Queue (.fifo required)", value=False)
    dlq_arn = st.text_input("Dead Letter Queue ARN (optional)")
    max_receive = st.slider("Max receive count before DLQ", 1, 10, 5)
    create_btn = st.button("Create Queue")
    if create_btn:
        try:
            attributes = {}
            if is_fifo:
                if not new_queue_name.endswith(".fifo"):
                    st.error("FIFO queues must end with .fifo")
                    st.stop()
                attributes["FifoQueue"] = "true"
                attributes["ContentBasedDeduplication"] = "true"
            if dlq_arn:
                redrive_policy = {
                    "deadLetterTargetArn": dlq_arn,
                    "maxReceiveCount": str(max_receive)
                }
                attributes["RedrivePolicy"] = json.dumps(redrive_policy)
            response = sqs_client.create_queue(
                QueueName=new_queue_name,
                Attributes=attributes
            )
            st.success(f"Queue created: {response['QueueUrl']}")
        except Exception as e:
            st.error(f"Queue creation failed: {e}")

# --- Load Queues ---
if st.button("Load SQS Queues"):
    try:
        queues = sqs_client.list_queues().get("QueueUrls", [])
        st.session_state['queues'] = queues
        if queues:
            st.success(f"Loaded {len(queues)} queues.")
        else:
            st.warning("No queues found.")
    except Exception as e:
        st.error(f"Error: {e}")

# --- Queue Operations ---
if 'queues' in st.session_state:
    queue_url = st.selectbox("Select Queue", st.session_state['queues'])

    # Dead Letter Queue visibility
    if st.button("Check DLQ Configuration"):
        try:
            attrs = sqs_client.get_queue_attributes(
                QueueUrl=queue_url,
                AttributeNames=["RedrivePolicy"]
            )["Attributes"]
            if "RedrivePolicy" in attrs:
                redrive = json.loads(attrs["RedrivePolicy"])
                st.info(f"DLQ: {redrive['deadLetterTargetArn']}, MaxReceiveCount: {redrive['maxReceiveCount']}")
            else:
                st.warning("No DLQ associated with this queue.")
        except Exception as e:
            st.error(f"Error fetching DLQ: {e}")

    # Send message
    with st.expander("Send a Message"):
        message = st.text_area("Message Body")
        msg_attr_key = st.text_input("Optional Attribute Key")
        msg_attr_val = st.text_input("Optional Attribute Value")
        if st.button("Send Message"):
            try:
                kwargs = {
                    "QueueUrl": queue_url,
                    "MessageBody": message
                }
                if msg_attr_key and msg_attr_val:
                    kwargs["MessageAttributes"] = {
                        msg_attr_key: {
                            'StringValue': msg_attr_val,
                            'DataType': 'String'
                        }
                    }
                response = sqs_client.send_message(**kwargs)
                st.success(f"Sent! Message ID: {response['MessageId']}")
            except Exception as e:
                st.error(f"Send failed: {e}")

    # Receive messages
    with st.expander("Receive and Delete Messages"):
        max_msgs = st.slider("Max Messages", 1, 10, 3)
        wait_time = st.slider("Wait Time (secs)", 0, 20, 5)
        if st.button("Receive Messages"):
            try:
                response = sqs_client.receive_message(
                    QueueUrl=queue_url,
                    MaxNumberOfMessages=max_msgs,
                    WaitTimeSeconds=wait_time,
                    MessageAttributeNames=["All"]
                )
                msgs = response.get("Messages", [])
                if msgs:
                    for msg in msgs:
                        st.markdown(f"**Message ID:** {msg['MessageId']}")
                        st.code(msg['Body'])
                        if msg.get("MessageAttributes"):
                            st.markdown("**Attributes:**")
                            st.json(msg["MessageAttributes"])
                        if st.button(f"Delete {msg['MessageId']}", key=msg['ReceiptHandle']):
                            try:
                                sqs_client.delete_message(
                                    QueueUrl=queue_url,
                                    ReceiptHandle=msg['ReceiptHandle']
                                )
                                st.success("Deleted successfully.")
                            except Exception as e:
                                st.error(f"Delete failed: {e}")
                else:
                    st.info("No messages available.")
            except Exception as e:
                st.error(f"Receive failed: {e}")
