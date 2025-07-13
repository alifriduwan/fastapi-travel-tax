FastAPI Travel Tax

ลงทะเบียนผู้ใช้ (Register)
POST /users/register

{
"email": "user1@example.com",
"phone_number": "0812345678",
"username": "user1",
"first_name": "John",
"last_name": "Doe",
"password": "Password123!"
}

Login
{
"identifier": "0812345678", // or user1@example.com
"password": "Password123!"
}

Authorize
username: user1
password: Password123!

Update for add role
{
"email": "newemail@example.com",
"phone_number": "0898765432",
"username": "newusername",
"first_name": "Jane",
"last_name": "Smith",
"roles": ["admin"]
}

- Create province only admin
- Update province only admin
- Delete province only admin
