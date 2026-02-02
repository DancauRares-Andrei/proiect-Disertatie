using System.Security.Cryptography;
using System.Text;

public class AesService
{
    public byte[] Encrypt(string plaintext, byte[] key, byte[] iv)
    {
        using var aes = Aes.Create();
        aes.Key = key;
        aes.IV = iv;

        using var encryptor = aes.CreateEncryptor();
        var bytes = Encoding.UTF8.GetBytes(plaintext);
        return encryptor.TransformFinalBlock(bytes, 0, bytes.Length);
    }
}

