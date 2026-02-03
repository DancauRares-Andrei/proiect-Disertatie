using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using System.Numerics;
using System.Security.Claims;
using System.Text;

namespace SecureRiscVServer.Components.Crypto
{
    [ApiController]
    [Route("api/crypto")]
    public class CryptoController : ControllerBase
    {
        private readonly SessionStore _sessions;
        private readonly AesService _aes;

        private static readonly RSA rsa = new();

        public CryptoController(SessionStore sessions, AesService aes)
        {
            _sessions = sessions;
            _aes = aes;

            if (rsa.PublicKey.n == 0)
                rsa.GenerateKeys(1024);
        }

        // ======================
        // RSA public key
        // ======================
        [HttpGet("publickey")]
        public IActionResult GetPublicKey()
        {
            var (e, n) = rsa.PublicKey;
            return Ok(new
            {
                e = e.ToString(),
                n = n.ToString()
            });
        }

        // ======================
        // Handshake RSA → AES
        // ======================
        [Authorize]
        [HttpPost("handshake")]
        public IActionResult Handshake([FromBody] HandshakeRequest request)
        {
            if (request?.EncryptedKey == null || request.EncryptedKey.Count != 1)
                return BadRequest("Expected single RSA block");

            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            // Parse single RSA block
            BigInteger c = BigInteger.Parse(request.EncryptedKey[0]);

            // Decrypt RSA
            byte[] decryptedFull = rsa.Decrypt(c); // de obicei 128 bytes pentru RSA-1024

            // Luăm ultimii 32 bytes: 16 AES key + 16 IV
            if (decryptedFull.Length < 32)
                return BadRequest("Invalid AES payload");

            byte[] decrypted = decryptedFull[^32..]; 

            var session = new SecureSession
            {
                AesKey = decrypted[..16],  // primele 16 bytes → AES key
                Iv     = decrypted[16..32] // următorii 16 bytes → IV
            };

            _sessions.Set(userId, session);

            Console.WriteLine($"[Handshake] OK for {userId}");
            Console.WriteLine($"AES Key: {BitConverter.ToString(session.AesKey)}");
            Console.WriteLine($"IV:      {BitConverter.ToString(session.Iv)}");

            return Ok();
        }


        // ======================
        // Send encrypted RISC-V instructions
        // ======================
        [Authorize]
        [HttpGet("next")]
        public IActionResult GetNextInstruction()
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            var session = _sessions.Get(userId);
            if (session == null)
                return BadRequest("No AES session");

            // 🔹 Instrucțiuni RISC-V (32-bit each)
            uint[] instructions =
            {
                0x003100B3, // ADD x1, x2, x3
                0x40428233, // SUB x4, x5, x6
                0x00000073  // ECALL
            };

            byte[] payload = new byte[instructions.Length * 4];
            for (int i = 0; i < instructions.Length; i++)
            {
                byte[] w = BitConverter.GetBytes(instructions[i]);
                Array.Copy(w, 0, payload, i * 4, 4);
            }

            byte[] encrypted = _aes.Encrypt(
                payload,
                session.AesKey,
                session.Iv
            );

            return Ok(Convert.ToBase64String(encrypted));
        }
    }
}
