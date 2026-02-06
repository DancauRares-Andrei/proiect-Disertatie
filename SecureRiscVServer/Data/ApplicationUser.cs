namespace SecureRiscVServer.Data
{
    public class ApplicationUser
    {
        public int Id { get; set; }            
        public string Username { get; set; } = null!;
        public string PasswordHash { get; set; } = null!;
    }
}
