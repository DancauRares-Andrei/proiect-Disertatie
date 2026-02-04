using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using SecureRiscVServer.Data;
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
        private readonly AESService _aes;

        private static readonly RSAService rsa = new();

        public CryptoController(SessionStore sessions, AESService aes)
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

        [Authorize]
        [HttpPost("instructions")]
        public IActionResult UploadInstructions(
            [FromBody] InstructionUploadRequest request,
            [FromServices] InstructionQueue queue)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            var parsed = new List<uint>();

            foreach (var s in request.Instructions)
            {
                if (!uint.TryParse(
                    s.Replace("0x", ""),
                    System.Globalization.NumberStyles.HexNumber,
                    null,
                    out var value))
                {
                    return BadRequest($"Invalid instruction: {s}");
                }

                parsed.Add(value);
            }

            queue.Enqueue(userId, parsed);

            return Ok($"Queued {parsed.Count} instructions");
        }


        [Authorize]
        [HttpGet("next")]
        public IActionResult GetNextInstruction(
    [FromServices] InstructionQueue queue)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (userId == null)
                return Unauthorized();

            var session = _sessions.Get(userId);
            if (session == null)
                return BadRequest("No AES session");

            uint[] instructions = queue.DequeueBatch(userId, max: 8);

            if (instructions.Length == 0)
                return NoContent(); // nimic de executat

            byte[] payload = new byte[instructions.Length * 4];

            for (int i = 0; i < instructions.Length; i++)
            {
                var w = BitConverter.GetBytes(instructions[i]); // little-endian
                Buffer.BlockCopy(w, 0, payload, i * 4, 4);
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
