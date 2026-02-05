using Microsoft.AspNetCore.Identity;

namespace SecureRiscVServer.Data
{
    // Entitatea simplificată pentru utilizator
    public class ApplicationUser
    {
        public int Id { get; set; }                // Primary Key
        public string Username { get; set; } = null!;
        public string PasswordHash { get; set; } = null!;
        // Poți adăuga câmpuri suplimentare după nevoie
    }
}
