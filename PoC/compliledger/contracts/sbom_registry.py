from pyteal import *

"""
SBOMRegistry Smart Contract
This contract stores artifact verification records on the Algorand blockchain
"""

# 64 zero bytes constant for padding (computed at import time)
ZERO64 = Bytes("base16", "0x" + "00" * 64)

def sbom_registry():
    """
    Main approval program for the SBOMRegistry smart contract
    """
    # Global state schema (minimal):
    # admin -> creator address (bytes)
    # oracle_address -> 32-byte app address public key (bytes)
    #
    # Per-artifact data is stored in Boxes with key = artifact_hash and value as a packed binary layout:
    #   0..7    : status (uint, Itob)            [0=pending,1=verified,2=failed]
    #   8..39   : submitter (32 bytes)
    #   40..47  : submitted_at (uint, Itob)
    #   48..55  : verified_at (uint, Itob)      [0 until verified]
    #   56..63  : profile_len (uint, Itob)
    #   64..    : profile_id (bytes)
    #   ...     : oscal_len (uint, Itob)
    #   ...     : oscal_cid (bytes)

    # --- Error code constants ---
    ERR_NOT_ADMIN = Bytes("ERR_NOT_ADMIN")
    ERR_NOT_ORACLE = Bytes("ERR_NOT_ORACLE")
    ERR_BAD_ARTIFACT_KEY = Bytes("ERR_BAD_ARTIFACT_KEY")
    ERR_PROFILE_TOO_LONG = Bytes("ERR_PROFILE_TOO_LONG")
    ERR_OSCAL_TOO_LONG = Bytes("ERR_OSCAL_TOO_LONG")
    ERR_BOX_EXISTS = Bytes("ERR_BOX_EXISTS")
    ERR_BOX_MISSING = Bytes("ERR_BOX_MISSING")
    ERR_BOX_CREATE_FAILED = Bytes("ERR_BOX_CREATE_FAILED")

    # Handle creation
    handle_creation = Seq([
        App.globalPut(Bytes("admin"), Global.creator_address()),
        App.globalPut(Bytes("oracle_address"), Global.zero_address()),
        Return(Int(1))
    ])
    
    # Set oracle address (admin only) to the provided 32-byte address (oracle app address)
    is_admin = Txn.sender() == App.globalGet(Bytes("admin"))
    set_oracle = Seq([
        If(Not(is_admin)).Then(Seq([
            Log(ERR_NOT_ADMIN),
            Return(Int(0))
        ])),
        App.globalPut(Bytes("oracle_address"), Txn.application_args[1]),
        Return(Int(1))
    ])

    # Submit verification request
    # Args: [0]"submit_verification", [1]artifact_hash, [2]profile_id
    artifact_hash = Txn.application_args[1]
    profile_id = Txn.application_args[2]
    
    # Fixed-size box value layout constants
    PROFILE_MAX = Int(64)
    OSCAL_MAX = Int(64)
    TOTAL_SIZE = Int(200)  # 8+32+8+8+8 + 64 + 8 + 64 = 200

    # Build initial packed box value with fixed-size fields
    initial_status = Itob(Int(0))
    submitter_bytes = Txn.sender()
    submitted_at = Itob(Global.latest_timestamp())
    verified_at = Itob(Int(0))
    profile_len_u64 = Len(profile_id)
    profile_len = Itob(profile_len_u64)
    profile_pad_len = PROFILE_MAX - profile_len_u64
    profile_padded = Concat(profile_id, Substring(ZERO64, Int(0), profile_pad_len))
    oscal_zero_field = Concat(Itob(Int(0)), Substring(ZERO64, Int(0), OSCAL_MAX))

    packed_initial = Concat(
        initial_status,              # 0..7
        submitter_bytes,             # 8..39 (32 bytes)
        submitted_at,                # 40..47
        verified_at,                 # 48..55
        profile_len,                 # 56..63
        profile_padded,              # 64..127 (64 bytes fixed)
        oscal_zero_field             # 128..199 (8 + 64)
    )

    # Pre-checks for submit: artifact key length, profile length, duplicate box
    mv_pre = BoxGet(artifact_hash)
    submit_verification = Seq([
        If(Or(Len(artifact_hash) != Int(32), Len(artifact_hash) == Int(0))).Then(Seq([
            Log(ERR_BAD_ARTIFACT_KEY),
            Return(Int(0))
        ])),
        If(Len(profile_id) > PROFILE_MAX).Then(Seq([
            Log(ERR_PROFILE_TOO_LONG),
            Return(Int(0))
        ])),
        mv_pre,
        If(mv_pre.hasValue()).Then(Seq([
            Log(ERR_BOX_EXISTS),
            Return(Int(0))
        ])),
        If(BoxCreate(artifact_hash, TOTAL_SIZE)).Then(Seq([
            BoxPut(artifact_hash, packed_initial),
            Return(Int(1))
        ])).Else(Seq([
            Log(ERR_BOX_CREATE_FAILED),
            Return(Int(0))
        ]))
    ])
    
    # Update verification from oracle
    # Args: [0]"update_verification", [1]artifact_hash, [2]oscal_cid, [3]status(int)
    is_oracle = Txn.sender() == App.globalGet(Bytes("oracle_address"))
    oscal_cid = Txn.application_args[2]
    verification_status = Btoi(Txn.application_args[3])
    
    # Offsets in the packed layout (with reserved OSCAL field space of 8+64 bytes)
    STATUS_OFF = Int(0)
    SUBMITTER_OFF = Int(8)
    SUBMITTED_AT_OFF = Int(40)
    VERIFIED_AT_OFF = Int(48)
    PROFILE_LEN_OFF = Int(56)
    PROFILE_ID_OFF = Int(64)

    mv = BoxGet(artifact_hash)
    profile_len_loaded = ScratchVar(TealType.uint64)
    oscal_off = ScratchVar(TealType.uint64)
    cid_field = ScratchVar(TealType.bytes)
    cid_pad_len = ScratchVar(TealType.uint64)

    update_verification = Seq([
        If(Not(is_oracle)).Then(Seq([
            Log(ERR_NOT_ORACLE),
            Return(Int(0))
        ])),
        mv,
        If(Not(mv.hasValue())).Then(Seq([
            Log(ERR_BOX_MISSING),
            Return(Int(0))
        ])),
        If(Len(oscal_cid) > OSCAL_MAX).Then(Seq([
            Log(ERR_OSCAL_TOO_LONG),
            Return(Int(0))
        ])),
        # Update status in place
        BoxReplace(artifact_hash, STATUS_OFF, Itob(verification_status)),
        # Update verified_at in place
        BoxReplace(artifact_hash, VERIFIED_AT_OFF, Itob(Global.latest_timestamp())),
        # Compute and write OSCAL field
        profile_len_loaded.store(Btoi(Extract(mv.value(), PROFILE_LEN_OFF, Int(8)))),
        oscal_off.store(Int(128)),
        cid_pad_len.store(OSCAL_MAX - Len(oscal_cid)),
        cid_field.store(Concat(Itob(Len(oscal_cid)), Concat(oscal_cid, Substring(ZERO64, Int(0), cid_pad_len.load())))),
        BoxReplace(artifact_hash, oscal_off.load(), cid_field.load()),
        Return(Int(1))
    ])
    
    # Query verification status
    # Args: [0]"query_verification", [1]artifact_hash
    # Log the status (first 8 bytes) from the box; if box missing, log 0
    mvq = BoxGet(artifact_hash)
    query_verification = Seq([
        mvq,
        If(
            mvq.hasValue(),
            Seq([
                Log(Extract(mvq.value(), Int(0), Int(8))),
                Return(Int(1))
            ]),
            Seq([
                Log(Itob(Int(0))),
                Return(Int(1))
            ])
        )
    ])
    
    # Program logic
    program = Cond(
        [Txn.application_id() == Int(0), handle_creation],
        [Txn.application_args[0] == Bytes("set_oracle"), set_oracle],
        [Txn.application_args[0] == Bytes("submit_verification"), submit_verification],
        [Txn.application_args[0] == Bytes("update_verification"), update_verification],
        [Txn.application_args[0] == Bytes("query_verification"), query_verification]
    )
    
    return program

def clear_state_program():
    """
    Clear state program for the SBOMRegistry contract
    """
    return Return(Int(1))

def compile_contract():
    """Compile the contract to TEAL files"""
    # Compile the approval program
    with open("CompliLedger_SbomRegistry_approval.teal", "w") as f:
        compiled = compileTeal(sbom_registry(), Mode.Application, version=8)
        f.write(compiled)
    
    # Compile the clear state program
    with open("CompliLedger_SbomRegistry_clear.teal", "w") as f:
        compiled = compileTeal(clear_state_program(), Mode.Application, version=8)
        f.write(compiled)
    
    print("CompliLedger SBOM Registry contract compiled to TEAL (v8)")

# Compile the approval program if run directly
if __name__ == "__main__":
    compile_contract()

