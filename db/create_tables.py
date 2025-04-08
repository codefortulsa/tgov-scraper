from src.models.meeting import Meeting
from botocore.exceptions import ClientError

def create_tables():
    print("Creating DynamoDB tables if they don't exist...")
    try:
        Meeting.create_table(wait=True, billing_mode="PAY_PER_REQUEST")
        print("Meeting table created!")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print("Meeting table already exists - skipping creation.")
        else:
            raise
    print("All tables ready!")

if __name__ == "__main__":
    create_tables()
