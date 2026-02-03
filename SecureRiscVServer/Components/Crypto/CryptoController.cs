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

            BigInteger c = BigInteger.Parse(request.EncryptedKey[0]);
            byte[] decrypted = rsa.Decrypt(c);

            if (decrypted.Length < 48)
                return BadRequest("Invalid AES payload");

            var session = new SecureSession
            {
                AesKey = decrypted[..32],
                Iv = decrypted[32..48]
            };

            _sessions.Set(userId, session);

            Console.WriteLine($"[Handshake] OK for {userId}");
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
