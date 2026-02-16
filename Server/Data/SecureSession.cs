namespace SecureRiscVServer.Data
{
    public class SecureSession
    {
        public byte[] AesKey { get; set; } = [];
        public byte[] Iv { get; set; } = [];
    }

}
