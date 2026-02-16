using Microsoft.EntityFrameworkCore;

namespace SecureRiscVServer.Data
{
    public class ApplicationDbContext : DbContext
    {
        public ApplicationDbContext(DbContextOptions<ApplicationDbContext> options)
            : base(options)
        {
        }

        // Tabelul pentru utilizatori
        public DbSet<ApplicationUser> Users { get; set; } = null!;
    }
}

