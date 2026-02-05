using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.AspNetCore.Components.Authorization;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using SecureRiscVServer.Components;
using SecureRiscVServer.Components.Crypto;
using SecureRiscVServer.Data;
using System.Text;

var builder = WebApplication.CreateBuilder(args);

var jwtKey = builder.Configuration["Jwt:Key"];

// ==========================
// Authentication & JWT
// ==========================
builder.Services.AddAuthentication(options =>
{
    options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(options =>
{
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = false,
        ValidateAudience = false,
        ValidateLifetime = true,
        ValidateIssuerSigningKey = true,
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtKey))
    };

    // Nu redirecta la login, ci returnează 401
    options.Events = new JwtBearerEvents
    {
        OnChallenge = context =>
        {
            context.HandleResponse();
            context.Response.StatusCode = 401;
            return Task.CompletedTask;
        }
    };
});

// ==========================
// Authorization
// ==========================
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("ApiPolicy", policy =>
    {
        policy.AddAuthenticationSchemes(JwtBearerDefaults.AuthenticationScheme);
        policy.RequireAuthenticatedUser();
    });
});

// ==========================
// Blazor Server / Razor Components
// ==========================
builder.Services.AddRazorComponents()
       .AddInteractiveServerComponents();

// Dacă vrei, poți folosi un AuthenticationStateProvider custom pe baza JWT
//builder.Services.AddScoped<AuthenticationStateProvider, JwtAuthenticationStateProvider>();

// ==========================
// Servicii aplicație
// ==========================
builder.Services.AddSingleton<InstructionQueue>();
builder.Services.AddSingleton<SessionStore>();
builder.Services.AddSingleton<AESService>();
builder.Services.AddSingleton<RSAService>();

// ==========================
// Database (fără Identity)
// ==========================
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection")
                       ?? throw new InvalidOperationException("Connection string 'DefaultConnection' not found.");
builder.Services.AddDbContext<ApplicationDbContext>(options =>
    options.UseSqlite(connectionString));

builder.Services.AddControllers();

var app = builder.Build();

// ==========================
// Middleware pipeline
// ==========================
if (app.Environment.IsDevelopment())
{
    app.UseMigrationsEndPoint();
}
else
{
    app.UseExceptionHandler("/Error", createScopeForErrors: true);
    app.UseHsts();
}

app.UseHttpsRedirection();
app.UseStaticFiles();
app.UseAntiforgery();

// JWT Authentication
app.UseAuthentication();
app.UseAuthorization();

// Blazor Server endpoints
app.MapControllers();
app.MapRazorComponents<App>()
   .AddInteractiveServerRenderMode();

app.Run();
